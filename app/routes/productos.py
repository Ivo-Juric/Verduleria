from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from db import get_db
from app.utils.auth_decorators import login_required

productos_bp = Blueprint("productos", __name__, url_prefix="/productos")


@productos_bp.route("/")
@login_required
def lista():
    db = get_db()
    productos = db.execute("""
        SELECT
            p.id,
            p.nombre,
            p.precio,
            p.stock,
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
        nombre = request.form["nombre"]
        categoria_id = request.form["categoria_id"]
        precio = float(request.form["precio"])
        stock = float(request.form["stock"])
        unidad_id = request.form["unidad_id"]

        db.execute("""
            UPDATE productos
            SET nombre=?, precio=?, stock=?, categoria_id=?, unidad_id=?
            WHERE id=?
        """, (nombre, precio, stock, categoria_id, unidad_id, id))
        db.commit()

        flash("Producto actualizado", "success")
        return redirect(url_for("productos.lista"))

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
    producto = db.execute("SELECT stock FROM productos WHERE id=?", (id,)).fetchone()
    if producto:
        return jsonify({"stock": producto["stock"]})
    return jsonify({"error": "Producto no encontrado"}), 404


@productos_bp.route("/autocomplete")
@login_required
def autocomplete():
    q = request.args.get("q", "").strip()
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

    return jsonify([{
        "id": r["id"],
        "nombre": r["nombre"],
        "precio": r["precio"],
        "unidad": r["unidad"]
    } for r in rows])
