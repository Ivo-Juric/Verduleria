from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from db import get_db
import datetime
from app.utils.auth_decorators import login_required

ventas_bp = Blueprint("ventas", __name__, url_prefix="/ventas")

@ventas_bp.route("/nueva", methods=["GET", "POST"])
@login_required
def nueva():
    db = get_db()
    productos = db.execute("SELECT * FROM productos").fetchall()

    if "carrito" not in session:
        session["carrito"] = []

    if request.method == "POST":
        producto_id = int(request.form["producto_id"])
        cantidad = float(request.form["cantidad"])

        producto = db.execute("SELECT * FROM productos WHERE id=?", (producto_id,)).fetchone()
        subtotal = producto["precio"] * cantidad

        session["carrito"].append({
            "producto_id": producto_id,
            "nombre": producto["nombre"],
            "cantidad": cantidad,
            "precio": producto["precio"],
            "subtotal": subtotal
        })
        session.modified = True

    total = sum(i["subtotal"] for i in session["carrito"])

    return render_template("ventas/nueva.html",
                           productos=productos,
                           carrito=session["carrito"],
                           total=total)

@ventas_bp.route("/quitar/<int:idx>")
@login_required
def quitar(idx):
    if "carrito" in session and 0 <= idx < len(session["carrito"]):
        session["carrito"].pop(idx)
        session.modified = True
    return redirect(url_for("ventas.nueva"))

@ventas_bp.route("/finalizar")
@login_required
def finalizar():
    db = get_db()

    carrito = session.get("carrito", [])
    if not carrito:
        flash("Carrito vacío", "warning")
        return redirect(url_for("ventas.nueva"))

    total = sum(i["subtotal"] for i in carrito)
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    cur = db.cursor()
    cur.execute("INSERT INTO ventas(fecha, total) VALUES (?, ?)", (fecha, total))
    venta_id = cur.lastrowid

    for i in carrito:
        cur.execute("""
        INSERT INTO detalle_venta(venta_id, producto_id, cantidad, subtotal)
        VALUES (?, ?, ?, ?)
        """, (venta_id, i["producto_id"], i["cantidad"], i["subtotal"]))

        db.execute("UPDATE productos SET stock = stock - ? WHERE id=?",
                   (i["cantidad"], i["producto_id"]))

    db.commit()

    ticket = carrito.copy()
    session["carrito"] = []
    session.modified = True

    return render_template("ventas/ticket.html",
                           ticket=ticket,
                           fecha=fecha,
                           total=total)
