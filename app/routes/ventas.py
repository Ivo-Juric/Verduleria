from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from db import get_db
import datetime
from datetime import timedelta
from app.utils.auth_decorators import login_required
from app.routes.productos import calcular_precio_con_oferta

ventas_bp = Blueprint("ventas", __name__, url_prefix="/ventas")

def get_adjusted_datetime():
    """
    Retorna la hora actual ajustada por -4 horas (zona Argentina UTC-3).
    El servidor está en USA West (UTC-7), así que restamos 4 horas.
    """
    return datetime.datetime.now() - timedelta(hours=4)

@ventas_bp.route("/nueva", methods=["GET", "POST"])
@login_required
def nueva():
    db = get_db()

    if "carrito" not in session:
        session["carrito"] = []

    if request.method == "POST":
        # leer el id del hidden y la cantidad
        producto_id = request.form.get("producto_id")
        if not producto_id:
            flash("Seleccioná un producto válido antes de agregar.", "warning")
            return redirect(url_for("ventas.nueva"))

        try:
            producto_id = int(producto_id)
            cantidad = float(request.form.get("cantidad", 1))
        except ValueError:
            flash("Valores inválidos.", "danger")
            return redirect(url_for("ventas.nueva"))

        # Validar que cantidad sea positiva
        if cantidad <= 0:
            flash("La cantidad debe ser mayor a 0.", "danger")
            return redirect(url_for("ventas.nueva"))

        producto = db.execute("SELECT * FROM productos WHERE id=?", (producto_id,)).fetchone()
        if not producto:
            flash("Producto no encontrado.", "danger")
            return redirect(url_for("ventas.nueva"))

        # Validar cantidad contra stock
        if cantidad > producto["stock"]:
            flash(f"Stock insuficiente. Disponible: {producto['stock']}", "danger")
            return redirect(url_for("ventas.nueva"))

        # Calcular precio con oferta aplicada
        info_precio = calcular_precio_con_oferta(db, producto_id, cantidad)
        precio_final = info_precio["precio_final"]
        subtotal = precio_final * cantidad

        # Traer unidad
        unidad = db.execute("SELECT nombre FROM unidades WHERE id=?", (producto["unidad_id"],)).fetchone()
        unidad_nombre = unidad["nombre"] if unidad else ""

        session["carrito"].append({
            "producto_id": producto_id,
            "nombre": producto["nombre"],
            "cantidad": cantidad,
            "precio": precio_final,
            "precio_original": info_precio["precio_original"],
            "subtotal": subtotal,
            "stock_disponible": producto["stock"],
            "unidad": unidad_nombre,
            "tiene_oferta": info_precio["tipo_oferta"] is not None,
            "descuento_aplicado": info_precio["descuento_aplicado"],
            "descripcion_oferta": info_precio["descripcion_oferta"]
        })
        session.modified = True
        flash(f"Producto agregado: {producto['nombre']}", "success")

    total = sum(i["subtotal"] for i in session.get("carrito", []))

    # Obtener carritos pendientes del usuario
    carritos_pendientes = db.execute("""
        SELECT id, nombre, total, fecha_creacion
        FROM carritos_pendientes
        WHERE usuario_id = ?
        ORDER BY fecha_creacion DESC
    """, (session.get("user_id"),)).fetchall()

    return render_template("ventas/nueva.html",
                           carrito=session.get("carrito", []),
                           total=total,
                           carritos_pendientes=carritos_pendientes)

@ventas_bp.route("/quitar/<int:idx>")
@login_required
def quitar(idx):
    if "carrito" in session and 0 <= idx < len(session["carrito"]):
        session["carrito"].pop(idx)
        session.modified = True
        flash("Producto removido del carrito", "info")
    return redirect(url_for("ventas.nueva"))

@ventas_bp.route("/guardar_pendiente", methods=["POST"])
@login_required
def guardar_pendiente():
    carrito = session.get("carrito", [])
    if not carrito:
        flash("Carrito vacío", "warning")
        return redirect(url_for("ventas.nueva"))

    nombre_carrito = request.form.get("nombre_carrito", f"Carrito {get_adjusted_datetime().strftime('%d/%m %H:%M')}")
    total = sum(i["subtotal"] for i in carrito)

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        INSERT INTO carritos_pendientes (usuario_id, nombre, total, fecha_creacion)
        VALUES (?, ?, ?, ?)
    """, (session.get("user_id"), nombre_carrito, total, get_adjusted_datetime().strftime("%Y-%m-%d %H:%M")))
    carrito_id = cur.lastrowid

    for i in carrito:
        cur.execute("""
            INSERT INTO detalle_carritos (carrito_id, producto_id, cantidad, subtotal)
            VALUES (?, ?, ?, ?)
        """, (carrito_id, i["producto_id"], i["cantidad"], i["subtotal"]))

    db.commit()

    session["carrito"] = []
    session.modified = True
    flash(f"Carrito guardado como '{nombre_carrito}'", "success")
    return redirect(url_for("ventas.nueva"))

@ventas_bp.route("/cargar_pendiente/<int:carrito_id>")
@login_required
def cargar_pendiente(carrito_id):
    db = get_db()

    # Verificar que el carrito pertenece al usuario
    carrito = db.execute("""
        SELECT * FROM carritos_pendientes
        WHERE id = ? AND usuario_id = ?
    """, (carrito_id, session.get("user_id"))).fetchone()

    if not carrito:
        flash("Carrito no encontrado", "danger")
        return redirect(url_for("ventas.nueva"))

    # Cargar detalles
    detalles = db.execute("""
        SELECT dc.producto_id, dc.cantidad, dc.subtotal, p.nombre, p.precio, p.stock, u.nombre as unidad
        FROM detalle_carritos dc
        JOIN productos p ON dc.producto_id = p.id
        LEFT JOIN unidades u ON p.unidad_id = u.id
        WHERE dc.carrito_id = ?
    """, (carrito_id,)).fetchall()

    session["carrito"] = []
    for detalle in detalles:
        # Recalcular precio con ofertas actuales
        info_precio = calcular_precio_con_oferta(db, detalle["producto_id"], detalle["cantidad"])
        precio_final = info_precio["precio_final"]
        subtotal_actual = precio_final * detalle["cantidad"]

        session["carrito"].append({
            "producto_id": detalle["producto_id"],
            "nombre": detalle["nombre"],
            "cantidad": detalle["cantidad"],
            "precio": precio_final,
            "precio_original": info_precio["precio_original"],
            "subtotal": subtotal_actual,
            "stock_disponible": detalle["stock"],
            "unidad": detalle["unidad"] or "",
            "tiene_oferta": info_precio["tipo_oferta"] is not None,
            "descuento_aplicado": info_precio["descuento_aplicado"],
            "descripcion_oferta": info_precio["descripcion_oferta"]
        })
    session.modified = True

    flash(f"Carrito '{carrito['nombre']}' cargado", "info")
    return redirect(url_for("ventas.nueva"))

@ventas_bp.route("/eliminar_pendiente/<int:carrito_id>")
@login_required
def eliminar_pendiente(carrito_id):
    db = get_db()

    carrito = db.execute("""
        SELECT * FROM carritos_pendientes
        WHERE id = ? AND usuario_id = ?
    """, (carrito_id, session.get("user_id"))).fetchone()

    if not carrito:
        flash("Carrito no encontrado", "danger")
        return redirect(url_for("ventas.nueva"))

    db.execute("DELETE FROM detalle_carritos WHERE carrito_id = ?", (carrito_id,))
    db.execute("DELETE FROM carritos_pendientes WHERE id = ?", (carrito_id,))
    db.commit()

    flash("Carrito eliminado", "info")
    return redirect(url_for("ventas.nueva"))

@ventas_bp.route("/finalizar", methods=["GET", "POST"])
@login_required
def finalizar():
    db = get_db()

    carrito = session.get("carrito", [])
    if not carrito:
        flash("Carrito vacío", "warning")
        return redirect(url_for("ventas.nueva"))

    total = sum(i["subtotal"] for i in carrito)

    # Inicializar métodos de pago en sesión
    if "metodos_pago_session" not in session:
        session["metodos_pago_session"] = []

    if request.method == "POST":
        # Procesar pago final
        metodos_pago = session.get("metodos_pago_session", [])
        monto_total_pago = sum(m["monto"] for m in metodos_pago)

        # Validar que el total pagado coincida
        if abs(monto_total_pago - total) > 0.01:
            flash(f"El monto total no coincide. Total: ${total}, Pagado: ${monto_total_pago}", "danger")
            return redirect(url_for("ventas.finalizar"))

        # Crear venta
        fecha = get_adjusted_datetime().strftime("%Y-%m-%d %H:%M")
        cur = db.cursor()
        cur.execute("INSERT INTO ventas(fecha, total) VALUES (?, ?)", (fecha, total))
        venta_id = cur.lastrowid

        # Detalles de ventas
        for i in carrito:
            cur.execute("""
            INSERT INTO detalle_ventas(venta_id, producto_id, cantidad, subtotal)
            VALUES (?, ?, ?, ?)
            """, (venta_id, i["producto_id"], i["cantidad"], i["subtotal"]))

            # Actualizar stock
            cur.execute("UPDATE productos SET stock = stock - ? WHERE id=?", (i["cantidad"], i["producto_id"]))

        # Registrar métodos de pago
        for pago in metodos_pago:
            metodo = db.execute("SELECT id FROM metodos_pago WHERE nombre = ?", (pago["metodo"],)).fetchone()
            if metodo:
                cur.execute("""
                    INSERT INTO detalle_pago (venta_id, metodo_id, monto)
                    VALUES (?, ?, ?)
                """, (venta_id, metodo["id"], pago["monto"]))

        db.commit()

        ticket = list(carrito)
        metodos_pago_ticket = list(metodos_pago)

        session["carrito"] = []
        session["metodos_pago_session"] = []
        session.modified = True

        return render_template("ventas/ticket.html",
                               ticket=ticket,
                               fecha=fecha,
                               total=total,
                               metodos_pago=metodos_pago_ticket)

    else:
        # GET: mostrar formulario de métodos de pago
        metodos = db.execute("SELECT * FROM metodos_pago ORDER BY nombre").fetchall()
        metodos_pago_session = session.get("metodos_pago_session", [])
        monto_pagado = sum(m["monto"] for m in metodos_pago_session)
        falta_pagar = total - monto_pagado

        return render_template("ventas/metodos_pago.html",
                               carrito=carrito,
                               total=total,
                               metodos=metodos,
                               metodos_pago_session=metodos_pago_session,
                               monto_pagado=monto_pagado,
                               falta_pagar=falta_pagar)

@ventas_bp.route("/agregar_metodo_pago", methods=["POST"])
@login_required
def agregar_metodo_pago():
    metodo_nombre = request.form.get("metodo")
    monto = request.form.get("monto", "0")

    try:
        monto = float(monto)
    except ValueError:
        flash("Monto inválido", "danger")
        return redirect(url_for("ventas.finalizar"))

    if monto <= 0:
        flash("El monto debe ser mayor a 0", "danger")
        return redirect(url_for("ventas.finalizar"))

    if "metodos_pago_session" not in session:
        session["metodos_pago_session"] = []

    session["metodos_pago_session"].append({
        "metodo": metodo_nombre,
        "monto": monto
    })
    session.modified = True

    flash(f"Método de pago agregado: {metodo_nombre} - ${monto}", "success")
    return redirect(url_for("ventas.finalizar"))

@ventas_bp.route("/quitar_metodo_pago/<int:idx>")
@login_required
def quitar_metodo_pago(idx):
    if "metodos_pago_session" in session and 0 <= idx < len(session["metodos_pago_session"]):
        session["metodos_pago_session"].pop(idx)
        session.modified = True
        flash("Método de pago removido", "info")
    return redirect(url_for("ventas.finalizar"))
