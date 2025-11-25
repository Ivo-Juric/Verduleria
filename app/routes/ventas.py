from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from db import get_db
import datetime
from app.utils.auth_decorators import login_required

ventas_bp = Blueprint("ventas", __name__, url_prefix="/ventas")

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

        subtotal = producto["precio"] * cantidad

        # Traer unidad
        unidad = db.execute("SELECT nombre FROM unidades WHERE id=?", (producto["unidad_id"],)).fetchone()
        unidad_nombre = unidad["nombre"] if unidad else ""

        session["carrito"].append({
            "producto_id": producto_id,
            "nombre": producto["nombre"],
            "cantidad": cantidad,
            "precio": producto["precio"],
            "subtotal": subtotal,
            "stock_disponible": producto["stock"],
            "unidad": unidad_nombre
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

    nombre_carrito = request.form.get("nombre_carrito", f"Carrito {datetime.datetime.now().strftime('%d/%m %H:%M')}")
    total = sum(i["subtotal"] for i in carrito)

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        INSERT INTO carritos_pendientes (usuario_id, nombre, total, fecha_creacion)
        VALUES (?, ?, ?, ?)
    """, (session.get("user_id"), nombre_carrito, total, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
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
        session["carrito"].append({
            "producto_id": detalle["producto_id"],
            "nombre": detalle["nombre"],
            "cantidad": detalle["cantidad"],
            "precio": detalle["precio"],
            "subtotal": detalle["subtotal"],
            "stock_disponible": detalle["stock"],
            "unidad": detalle["unidad"] or ""
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

    if request.method == "POST":
        # Procesar métodos de pago
        total = sum(i["subtotal"] for i in carrito)
        metodos_pago = {}
        monto_total_pago = 0

        # Recopilar métodos de pago
        for metodo in ["Efectivo", "Transferencia", "QR", "Tarjeta de Débito"]:
            monto = request.form.get(f"monto_{metodo}", "0")
            try:
                monto = float(monto)
                if monto > 0:
                    metodos_pago[metodo] = monto
                    monto_total_pago += monto
            except ValueError:
                pass

        # Validar que el total pagado coincida
        if abs(monto_total_pago - total) > 0.01:
            flash(f"El monto total no coincide. Total: ${total}, Pagado: ${monto_total_pago}", "danger")
            metodos = db.execute("SELECT * FROM metodos_pago ORDER BY nombre").fetchall()
            return render_template("ventas/metodos_pago.html",
                                   carrito=carrito,
                                   total=total,
                                   metodos=metodos)

        # Crear venta
        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
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
        for metodo_nombre, monto in metodos_pago.items():
            metodo = db.execute("SELECT id FROM metodos_pago WHERE nombre = ?", (metodo_nombre,)).fetchone()
            if metodo:
                cur.execute("""
                    INSERT INTO detalle_pago (venta_id, metodo_id, monto)
                    VALUES (?, ?, ?)
                """, (venta_id, metodo["id"], monto))

        db.commit()

        ticket = list(carrito)
        session["carrito"] = []
        session.modified = True

        return render_template("ventas/ticket.html",
                               ticket=ticket,
                               fecha=fecha,
                               total=total,
                               metodos_pago=metodos_pago)

    else:
        # GET: mostrar formulario de métodos de pago
        total = sum(i["subtotal"] for i in carrito)
        metodos = db.execute("SELECT * FROM metodos_pago ORDER BY nombre").fetchall()
        return render_template("ventas/metodos_pago.html",
                               carrito=carrito,
                               total=total,
                               metodos=metodos)
