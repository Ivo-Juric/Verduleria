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

    if request.method == "POST":
        cantidad = float(request.form["cantidad"])
        proveedor = request.form["proveedor"]

        db.execute("""
            UPDATE productos
            SET stock = stock + ?
            WHERE id=?
        """, (cantidad, id))
        db.commit()

        flash(f"Stock ingresado: +{cantidad} unidades de {proveedor}", "success")
        return redirect(url_for("productos.lista"))

    return render_template("productos/gestionar_stock.html", producto=producto)


@productos_bp.route("/autocomplete")
@login_required
def autocomplete():
    q = request.args.get("q", "")
    db = get_db()

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
