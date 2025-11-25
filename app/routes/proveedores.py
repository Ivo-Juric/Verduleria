from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import get_db
from app.utils.auth_decorators import login_required, admin_required

proveedores_bp = Blueprint("proveedores", __name__, url_prefix="/proveedores")


@proveedores_bp.route("/")
@login_required
def lista():
    db = get_db()
    proveedores = db.execute("""
        SELECT
            p.id,
            p.nombre,
            p.contacto,
            p.telefono,
            p.email,
            COUNT(i.id) as total_compras
        FROM proveedores p
        LEFT JOIN ingresos_stock i ON p.id = i.proveedor_id
        GROUP BY p.id
        ORDER BY p.nombre
    """).fetchall()

    return render_template("proveedores/lista.html", proveedores=proveedores)


@proveedores_bp.route("/nuevo", methods=["GET", "POST"])
@admin_required
def nuevo():
    if request.method == "POST":
        nombre = request.form["nombre"]
        contacto = request.form.get("contacto", "")
        telefono = request.form.get("telefono", "")
        email = request.form.get("email", "")

        db = get_db()
        try:
            db.execute("""
                INSERT INTO proveedores (nombre, contacto, telefono, email)
                VALUES (?, ?, ?, ?)
            """, (nombre, contacto, telefono, email))
            db.commit()
            flash("Proveedor creado correctamente", "success")
            return redirect(url_for("proveedores.lista"))
        except Exception as e:
            flash("Error: ese proveedor ya existe", "danger")

    return render_template("proveedores/nuevo.html")


@proveedores_bp.route("/editar/<int:id>", methods=["GET", "POST"])
@admin_required
def editar(id):
    db = get_db()
    proveedor = db.execute("SELECT * FROM proveedores WHERE id=?", (id,)).fetchone()

    if request.method == "POST":
        nombre = request.form["nombre"]
        contacto = request.form.get("contacto", "")
        telefono = request.form.get("telefono", "")
        email = request.form.get("email", "")

        db.execute("""
            UPDATE proveedores
            SET nombre=?, contacto=?, telefono=?, email=?
            WHERE id=?
        """, (nombre, contacto, telefono, email, id))
        db.commit()

        flash("Proveedor actualizado", "success")
        return redirect(url_for("proveedores.lista"))

    return render_template("proveedores/editar.html", proveedor=proveedor)


@proveedores_bp.route("/delete/<int:id>")
@admin_required
def delete(id):
    db = get_db()

    # Verificar si tiene ingresos de stock
    ingreso = db.execute(
        "SELECT COUNT(*) FROM ingresos_stock WHERE proveedor_id=?", (id,)
    ).fetchone()[0]

    if ingreso > 0:
        flash("No se puede eliminar: el proveedor tiene registros de compra", "danger")
        return redirect(url_for("proveedores.lista"))

    db.execute("DELETE FROM proveedores WHERE id=?", (id,))
    db.commit()
    flash("Proveedor eliminado", "danger")
    return redirect(url_for("proveedores.lista"))


@proveedores_bp.route("/<int:id>/ingresos")
@login_required
def ingresos(id):
    db = get_db()
    proveedor = db.execute("SELECT * FROM proveedores WHERE id=?", (id,)).fetchone()

    ingresos_stock = db.execute("""
        SELECT
            i.id,
            i.fecha,
            p.nombre AS producto,
            i.cantidad,
            u.nombre AS unidad,
            i.precio_unitario,
            (i.cantidad * COALESCE(i.precio_unitario, 0)) as total
        FROM ingresos_stock i
        JOIN productos p ON i.producto_id = p.id
        LEFT JOIN unidades u ON p.unidad_id = u.id
        WHERE i.proveedor_id = ?
        ORDER BY i.fecha DESC
    """, (id,)).fetchall()

    return render_template("proveedores/ingresos.html",
                           proveedor=proveedor,
                           ingresos=ingresos_stock)
