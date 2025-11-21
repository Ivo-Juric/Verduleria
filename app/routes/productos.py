from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from db import get_db
import datetime
from app.utils.auth_decorators import login_required

productos_bp = Blueprint("productos", __name__, url_prefix="/productos")

@productos_bp.route("/")
@login_required
def lista():
    db = get_db()
    productos = db.execute("SELECT * FROM productos").fetchall()
    return render_template("productos/lista.html", productos=productos)

@productos_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
def nuevo():
    if request.method == "POST":
        nombre = request.form["nombre"]
        categoria = request.form["categoria"]
        precio = float(request.form["precio"])
        stock = float(request.form["stock"])
        unidad = request.form["unidad"]

        db = get_db()
        db.execute("""
            INSERT INTO productos(nombre, categoria, precio, stock, unidad)
            VALUES (?, ?, ?, ?, ?)
        """, (nombre, categoria, precio, stock, unidad))
        db.commit()

        flash("Producto agregado", "success")
        return redirect(url_for("productos.lista"))

    return render_template("productos/nuevo.html")

@productos_bp.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    db = get_db()
    producto = db.execute("SELECT * FROM productos WHERE id=?", (id,)).fetchone()

    if request.method == "POST":
        nombre = request.form["nombre"]
        categoria = request.form["categoria"]
        precio = float(request.form["precio"])
        stock = float(request.form["stock"])
        unidad = request.form["unidad"]

        db.execute("""
            UPDATE productos SET nombre=?, categoria=?, precio=?, stock=?, unidad=?
            WHERE id=?
        """, (nombre, categoria, precio, stock, unidad, id))
        db.commit()

        flash("Producto actualizado", "success")
        return redirect(url_for("productos.lista"))

    return render_template("productos/editar.html", producto=producto)

@productos_bp.route("/delete/<int:id>")
@login_required
def delete(id):
    db = get_db()
    db.execute("DELETE FROM productos WHERE id=?", (id,))
    db.commit()
    flash("Producto eliminado", "danger")
    return redirect(url_for("productos.lista"))

@productos_bp.route("/autocomplete")
@login_required
def autocomplete():
    q = request.args.get("q", "")
    db = get_db()
    rows = db.execute("""
        SELECT id, nombre, precio, unidad FROM productos
        WHERE nombre LIKE ?
        LIMIT 10
    """, (f"%{q}%",)).fetchall()

    return jsonify([{
        "id": r["id"],
        "nombre": r["nombre"],
        "precio": r["precio"],
        "unidad": r["unidad"]
    } for r in rows])
