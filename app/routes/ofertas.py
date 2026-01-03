from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from db import get_db
from app.utils.auth_decorators import login_required, admin_required
from datetime import datetime

ofertas_bp = Blueprint("ofertas", __name__, url_prefix="/ofertas")

@ofertas_bp.route("/")
@login_required
@admin_required
def index():
    db = get_db()
    ofertas = db.execute("""
        SELECT o.*,
               COUNT(op.id) as productos_afectados
        FROM ofertas o
        LEFT JOIN oferta_productos op ON o.id = op.oferta_id
        GROUP BY o.id
        ORDER BY o.fecha_inicio DESC
    """).fetchall()

    return render_template("ofertas/index.html", ofertas=ofertas)

@ofertas_bp.route("/nueva", methods=["GET", "POST"])
@login_required
@admin_required
def nueva():
    db = get_db()

    if request.method == "POST":
        nombre = request.form.get("nombre")
        descripcion = request.form.get("descripcion")
        fecha_inicio = request.form.get("fecha_inicio")
        fecha_fin = request.form.get("fecha_fin")
        tipo_oferta = request.form.get("tipo_oferta")
        descuento_global = request.form.get("descuento_global", 0)

        if not all([nombre, fecha_inicio, fecha_fin, tipo_oferta]):
            flash("Todos los campos son obligatorios", "danger")
            return redirect(url_for("ofertas.nueva"))

        try:
            descuento_global = float(descuento_global) if descuento_global else 0
        except ValueError:
            flash("Descuento global debe ser un número", "danger")
            return redirect(url_for("ofertas.nueva"))

        cur = db.cursor()
        cur.execute("""
            INSERT INTO ofertas (nombre, descripcion, fecha_inicio, fecha_fin, tipo_oferta, descuento_global)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (nombre, descripcion, fecha_inicio, fecha_fin, tipo_oferta, descuento_global))

        oferta_id = cur.lastrowid

        # Procesar productos según el tipo de oferta
        if tipo_oferta == "individual_precio":
            productos = request.form.getlist("producto_id[]")
            precios = request.form.getlist("precio_oferta[]")

            for prod_id, precio in zip(productos, precios):
                if prod_id and precio:
                    try:
                        precio_float = float(precio)
                        cur.execute("""
                            INSERT INTO oferta_productos (oferta_id, producto_id, precio_oferta)
                            VALUES (?, ?, ?)
                        """, (oferta_id, prod_id, precio_float))
                    except ValueError:
                        continue

        elif tipo_oferta == "individual_cantidad":
            productos = request.form.getlist("producto_id[]")
            cantidades = request.form.getlist("cantidad_minima[]")
            descuentos = request.form.getlist("descuento_porcentaje[]")

            for prod_id, cant, desc in zip(productos, cantidades, descuentos):
                if prod_id and cant and desc:
                    try:
                        cant_int = int(cant)
                        desc_float = float(desc)
                        cur.execute("""
                            INSERT INTO oferta_productos (oferta_id, producto_id, cantidad_minima, descuento_porcentaje)
                            VALUES (?, ?, ?, ?)
                        """, (oferta_id, prod_id, cant_int, desc_float))
                    except ValueError:
                        continue

        elif tipo_oferta == "conjunto_descuento":
            productos = request.form.getlist("producto_id[]")
            descuentos = request.form.getlist("descuento_porcentaje[]")

            for prod_id, desc in zip(productos, descuentos):
                if prod_id and desc:
                    try:
                        desc_float = float(desc)
                        cur.execute("""
                            INSERT INTO oferta_productos (oferta_id, producto_id, descuento_porcentaje)
                            VALUES (?, ?, ?)
                        """, (oferta_id, prod_id, desc_float))
                    except ValueError:
                        continue

        db.commit()
        flash("Oferta creada exitosamente", "success")
        return redirect(url_for("ofertas.index"))

    productos = db.execute("SELECT id, nombre FROM productos ORDER BY nombre").fetchall()
    return render_template("ofertas/nueva.html", productos=productos)

@ofertas_bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def editar(id):
    db = get_db()
    oferta = db.execute("SELECT * FROM ofertas WHERE id = ?", (id,)).fetchone()
    if not oferta:
        flash("Oferta no encontrada", "danger")
        return redirect(url_for("ofertas.index"))

    if request.method == "POST":
        nombre = request.form.get("nombre")
        descripcion = request.form.get("descripcion")
        fecha_inicio = request.form.get("fecha_inicio")
        fecha_fin = request.form.get("fecha_fin")
        tipo_oferta = request.form.get("tipo_oferta")
        descuento_global = request.form.get("descuento_global", 0)
        activo = 1 if request.form.get("activo") else 0

        if not all([nombre, fecha_inicio, fecha_fin, tipo_oferta]):
            flash("Todos los campos son obligatorios", "danger")
            return redirect(url_for("ofertas.editar", id=id))

        try:
            descuento_global = float(descuento_global) if descuento_global else 0
        except ValueError:
            flash("Descuento global debe ser un número", "danger")
            return redirect(url_for("ofertas.editar", id=id))

        cur = db.cursor()
        cur.execute("""
            UPDATE ofertas
            SET nombre=?, descripcion=?, fecha_inicio=?, fecha_fin=?,
                tipo_oferta=?, descuento_global=?, activo=?
            WHERE id=?
        """, (nombre, descripcion, fecha_inicio, fecha_fin, tipo_oferta, descuento_global, activo, id))

        # Eliminar productos anteriores y agregar nuevos
        cur.execute("DELETE FROM oferta_productos WHERE oferta_id = ?", (id,))

        # Procesar productos según el tipo de oferta (igual que en nueva)
        if tipo_oferta == "individual_precio":
            productos = request.form.getlist("producto_id[]")
            precios = request.form.getlist("precio_oferta[]")

            for prod_id, precio in zip(productos, precios):
                if prod_id and precio:
                    try:
                        precio_float = float(precio)
                        cur.execute("""
                            INSERT INTO oferta_productos (oferta_id, producto_id, precio_oferta)
                            VALUES (?, ?, ?)
                        """, (id, prod_id, precio_float))
                    except ValueError:
                        continue

        elif tipo_oferta == "individual_cantidad":
            productos = request.form.getlist("producto_id[]")
            cantidades = request.form.getlist("cantidad_minima[]")
            descuentos = request.form.getlist("descuento_porcentaje[]")

            for prod_id, cant, desc in zip(productos, cantidades, descuentos):
                if prod_id and cant and desc:
                    try:
                        cant_int = int(cant)
                        desc_float = float(desc)
                        cur.execute("""
                            INSERT INTO oferta_productos (oferta_id, producto_id, cantidad_minima, descuento_porcentaje)
                            VALUES (?, ?, ?, ?)
                        """, (id, prod_id, cant_int, desc_float))
                    except ValueError:
                        continue

        elif tipo_oferta == "conjunto_descuento":
            productos = request.form.getlist("producto_id[]")
            descuentos = request.form.getlist("descuento_porcentaje[]")

            for prod_id, desc in zip(productos, descuentos):
                if prod_id and desc:
                    try:
                        desc_float = float(desc)
                        cur.execute("""
                            INSERT INTO oferta_productos (oferta_id, producto_id, descuento_porcentaje)
                            VALUES (?, ?, ?)
                        """, (id, prod_id, desc_float))
                    except ValueError:
                        continue

        db.commit()
        flash("Oferta actualizada exitosamente", "success")
        return redirect(url_for("ofertas.index"))

    productos_oferta = db.execute("""
        SELECT op.*, p.nombre as producto_nombre
        FROM oferta_productos op
        JOIN productos p ON op.producto_id = p.id
        WHERE op.oferta_id = ?
    """, (id,)).fetchall()

    productos = db.execute("SELECT id, nombre FROM productos ORDER BY nombre").fetchall()
    return render_template("ofertas/editar.html", oferta=oferta, productos_oferta=productos_oferta, productos=productos)

@ofertas_bp.route("/<int:id>/eliminar", methods=["POST"])
@login_required
@admin_required
def eliminar(id):
    db = get_db()
    db.execute("DELETE FROM ofertas WHERE id = ?", (id,))
    db.commit()
    flash("Oferta eliminada", "success")
    return redirect(url_for("ofertas.index"))

@ofertas_bp.route("/<int:id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle(id):
    db = get_db()
    oferta = db.execute("SELECT activo FROM ofertas WHERE id = ?", (id,)).fetchone()
    if oferta:
        nuevo_estado = 0 if oferta["activo"] else 1
        db.execute("UPDATE ofertas SET activo = ? WHERE id = ?", (nuevo_estado, id))
        db.commit()
        flash(f"Oferta {'activada' if nuevo_estado else 'desactivada'}", "success")
    return redirect(url_for("ofertas.index"))