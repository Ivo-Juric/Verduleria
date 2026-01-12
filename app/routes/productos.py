from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from db import get_db
from app.utils.auth_decorators import login_required
from datetime import datetime
from app.routes.ofertas import desactivar_ofertas_expiradas

productos_bp = Blueprint("productos", __name__, url_prefix="/productos")

def calcular_precio_con_oferta(db, producto_id, cantidad=1):
    """
    Calcula el precio final de un producto considerando ofertas activas.
    Retorna un dict con precio_final, descuento_aplicado, tipo_oferta, etc.
    """
    # Desactivar ofertas expiradas antes de calcular
    desactivar_ofertas_expiradas()

    producto = db.execute("SELECT precio FROM productos WHERE id = ?", (producto_id,)).fetchone()
    if not producto:
        return {"precio_final": 0, "descuento_aplicado": 0, "tipo_oferta": None}

    precio_original = producto["precio"]
    precio_final = precio_original
    descuento_aplicado = 0
    tipo_oferta = None
    descripcion_oferta = None

    # Buscar ofertas activas para este producto
    ahora = datetime.now().strftime("%Y-%m-%dT%H:%M")

    ofertas = db.execute("""
        SELECT o.*, op.*
        FROM ofertas o
        JOIN oferta_productos op ON o.id = op.oferta_id
        WHERE op.producto_id = ?
        AND o.activo = 1
        AND o.fecha_inicio <= ?
        AND o.fecha_fin >= ?
        ORDER BY o.fecha_inicio DESC
    """, (producto_id, ahora, ahora)).fetchall()

    for oferta in ofertas:
        if oferta["tipo_oferta"] == "individual_precio" and oferta["precio_oferta"]:
            # Precio fijo
            precio_final = oferta["precio_oferta"]
            descuento_aplicado = precio_original - precio_final
            tipo_oferta = "precio_fijo"
            descripcion_oferta = f"Precio especial: ${precio_final}"
            break  # Prioridad a precio fijo

        elif oferta["tipo_oferta"] == "individual_cantidad" and oferta["cantidad_minima"] and cantidad >= oferta["cantidad_minima"]:
            # Descuento por cantidad
            descuento = precio_original * (oferta["descuento_porcentaje"] / 100)
            precio_final = precio_original - descuento
            descuento_aplicado = descuento
            tipo_oferta = "cantidad"
            descripcion_oferta = f"Descuento por cantidad: {oferta['descuento_porcentaje']}%"
            break  # Prioridad alta

        elif oferta["tipo_oferta"] == "conjunto_descuento":
            # Descuento de conjunto (puede ser global o específico)
            descuento_pct = oferta["descuento_global"] or oferta["descuento_porcentaje"] or 0
            descuento = precio_original * (descuento_pct / 100)
            precio_final = precio_original - descuento
            descuento_aplicado = descuento
            tipo_oferta = "conjunto"
            descripcion_oferta = f"Descuento conjunto: {descuento_pct}%"
            # No break, puede haber mejores ofertas

    return {
        "precio_final": precio_final,
        "descuento_aplicado": descuento_aplicado,
        "tipo_oferta": tipo_oferta,
        "descripcion_oferta": descripcion_oferta,
        "precio_original": precio_original
    }


@productos_bp.route("/")
@login_required
def lista():
    db = get_db()
    productos = db.execute("""
        SELECT
            p.id,
            p.nombre,
            p.precio,
            p.stock - p.stock_defectuoso AS stock_disponible,
            p.stock_defectuoso,
            c.nombre AS categoria,
            u.nombre AS unidad
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        LEFT JOIN unidades u ON p.unidad_id = u.id
    """).fetchall()

    return render_template("productos/lista.html", productos=productos)


@productos_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
def nuevo():
    db = get_db()

    # Traer categorías y unidades
    categorias = db.execute("SELECT * FROM categorias").fetchall()
    unidades = db.execute("SELECT * FROM unidades").fetchall()

    if request.method == "POST":
        nombre = request.form["nombre"]
        categoria_id = request.form["categoria_id"]
        precio = float(request.form["precio"])
        stock = float(request.form["stock"])
        unidad_id = request.form["unidad_id"]

        db.execute("""
            INSERT INTO productos(nombre, precio, stock, categoria_id, unidad_id)
            VALUES (?, ?, ?, ?, ?)
        """, (nombre, precio, stock, categoria_id, unidad_id))
        db.commit()

        flash("Producto agregado", "success")
        return redirect(url_for("productos.lista"))

    return render_template("productos/nuevo.html",
                           categorias=categorias,
                           unidades=unidades)


@productos_bp.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    db = get_db()

    producto = db.execute("SELECT * FROM productos WHERE id=?", (id,)).fetchone()
    categorias = db.execute("SELECT * FROM categorias").fetchall()
    unidades = db.execute("SELECT * FROM unidades").fetchall()

    if request.method == "POST":
        if "actualizar_producto" in request.form:
            nombre = request.form["nombre"]
            categoria_id = request.form["categoria_id"]
            precio = float(request.form["precio"])
            unidad_id = request.form["unidad_id"]

            db.execute("""
                UPDATE productos
                SET nombre=?, precio=?, categoria_id=?, unidad_id=?
                WHERE id=?
            """, (nombre, precio, categoria_id, unidad_id, id))
            db.commit()

            flash("Producto actualizado", "success")
            return redirect(url_for("productos.editar", id=id))

        elif "marcar_defectuoso" in request.form:
            cantidad_defectuosa = float(request.form["cantidad_defectuosa"])
            if cantidad_defectuosa > 0:
                stock_disponible = producto["stock"] - producto["stock_defectuoso"]
                if cantidad_defectuosa <= stock_disponible:
                    db.execute("""
                        UPDATE productos
                        SET stock_defectuoso = stock_defectuoso + ?
                        WHERE id=?
                    """, (cantidad_defectuosa, id))
                    db.commit()
                    flash(f"Se marcaron {cantidad_defectuosa} unidades como defectuosas", "warning")
                else:
                    flash("Cantidad excede el stock disponible", "danger")
            return redirect(url_for("productos.editar", id=id))

        elif "tirar_basura" in request.form:
            cantidad_basura = float(request.form["cantidad_basura"])
            if cantidad_basura > 0:
                if cantidad_basura <= producto["stock_defectuoso"]:
                    db.execute("""
                        UPDATE productos
                        SET stock_defectuoso = stock_defectuoso - ?,
                            stock = stock - ?
                        WHERE id=?
                    """, (cantidad_basura, cantidad_basura, id))
                    db.commit()
                    flash(f"Se tiraron {cantidad_basura} unidades defectuosas a la basura", "danger")
                else:
                    flash("Cantidad excede el stock defectuoso", "danger")
            return redirect(url_for("productos.editar", id=id))

    return render_template("productos/editar.html",
                           producto=producto,
                           categorias=categorias,
                           unidades=unidades)


@productos_bp.route("/delete/<int:id>")
@login_required
def delete(id):
    db = get_db()
    db.execute("DELETE FROM productos WHERE id=?", (id,))
    db.commit()
    flash("Producto eliminado", "danger")
    return redirect(url_for("productos.lista"))


@productos_bp.route("/stock/<int:id>", methods=["GET", "POST"])
@login_required
def gestionar_stock(id):
    db = get_db()

    producto = db.execute("SELECT * FROM productos WHERE id=?", (id,)).fetchone()
    proveedores = db.execute("SELECT * FROM proveedores ORDER BY nombre").fetchall()

    if request.method == "POST":
        cantidad = float(request.form["cantidad"])
        proveedor_id = request.form["proveedor_id"]
        precio_unitario = request.form.get("precio_unitario", "0")

        try:
            precio_unitario = float(precio_unitario) if precio_unitario else None
        except ValueError:
            precio_unitario = None

        # Registrar ingreso de stock
        db.execute("""
            INSERT INTO ingresos_stock (producto_id, proveedor_id, cantidad, fecha, precio_unitario)
            VALUES (?, ?, ?, datetime('now', 'localtime'), ?)
        """, (id, proveedor_id, cantidad, precio_unitario))

        # Actualizar stock del producto
        db.execute("""
            UPDATE productos
            SET stock = stock + ?
            WHERE id=?
        """, (cantidad, id))

        db.commit()

        proveedor = db.execute("SELECT nombre FROM proveedores WHERE id=?", (proveedor_id,)).fetchone()
        flash(f"Stock ingresado: +{cantidad} unidades de {proveedor['nombre']}", "success")
        return redirect(url_for("productos.lista"))

    return render_template("productos/gestionar_stock.html",
                           producto=producto,
                           proveedores=proveedores)
@productos_bp.route("/stock/<int:id>")
@login_required
def obtener_stock(id):
    db = get_db()
    producto = db.execute("SELECT stock - stock_defectuoso AS stock_disponible FROM productos WHERE id=?", (id,)).fetchone()
    if producto:
        return jsonify({"stock": producto["stock_disponible"]})
    return jsonify({"error": "Producto no encontrado"}), 404


@productos_bp.route("/autocomplete")
@login_required
def autocomplete():
    q = request.args.get("q", "").strip()
    cantidad = int(request.args.get("cantidad", 1))  # Para calcular descuentos por cantidad
    db = get_db()

    # Intenta buscar por ID primero si es un número
    rows = []
    try:
        producto_id = int(q)
        rows = db.execute("""
            SELECT
                p.id,
                p.nombre,
                p.precio,
                u.nombre AS unidad
            FROM productos p
            LEFT JOIN unidades u ON p.unidad_id = u.id
            WHERE p.id = ?
            LIMIT 10
        """, (producto_id,)).fetchall()
    except ValueError:
        pass

    # Si no encontró por ID o no es número, busca por nombre
    if not rows:
        rows = db.execute("""
            SELECT
                p.id,
                p.nombre,
                p.precio,
                u.nombre AS unidad
            FROM productos p
            LEFT JOIN unidades u ON p.unidad_id = u.id
            WHERE p.nombre LIKE ?
            LIMIT 10
        """, (f"%{q}%",)).fetchall()

    # Calcular precios con ofertas para cada producto
    resultados = []
    for r in rows:
        info_oferta = calcular_precio_con_oferta(db, r["id"], cantidad)
        resultados.append({
            "id": r["id"],
            "nombre": r["nombre"],
            "precio": info_oferta["precio_final"],
            "precio_original": info_oferta["precio_original"],
            "unidad": r["unidad"],
            "tiene_oferta": info_oferta["tipo_oferta"] is not None,
            "descuento_aplicado": info_oferta["descuento_aplicado"],
            "descripcion_oferta": info_oferta["descripcion_oferta"]
        })

    return jsonify(resultados)
