from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_db, hash_pass
from app.utils.auth_decorators import login_required, admin_required

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


# -------------------------------
# LISTAR USUARIOS (ADMIN)
# -------------------------------
@usuarios_bp.route("/")
@admin_required
def index():
    db = get_db()
    lista = db.execute("SELECT * FROM usuarios").fetchall()
    return render_template("usuarios/index.html", usuarios=lista)


# -------------------------------
# CREAR USUARIO (ADMIN)
# -------------------------------
@usuarios_bp.route("/nuevo", methods=["GET", "POST"])
@admin_required
def nuevo():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        rol = request.form["role"]

        db = get_db()
        try:
            db.execute(
                "INSERT INTO usuarios (username, password_hash, role) VALUES (?, ?, ?)",
                (u, hash_pass(p), rol)
            )
            db.commit()
            flash("Usuario creado correctamente", "success")
            return redirect(url_for("usuarios.index"))
        except:
            flash("Ese usuario ya existe", "danger")

    return render_template("usuarios/nuevo.html")


# -------------------------------
# EDITAR USUARIO (ADMIN)
# -------------------------------
@usuarios_bp.route("/editar/<int:user_id>", methods=["GET", "POST"])
@admin_required
def editar(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM usuarios WHERE id=?", (user_id,)).fetchone()

    if not user:
        flash("Usuario no encontrado", "danger")
        return redirect(url_for("usuarios.index"))

    if request.method == "POST":
        username = request.form["username"]
        role = request.form["role"]

        db.execute(
            "UPDATE usuarios SET username=?, role=? WHERE id=?",
            (username, role, user_id)
        )
        db.commit()

        flash("Usuario actualizado correctamente", "success")
        return redirect(url_for("usuarios.index"))

    return render_template("usuarios/editar.html", user=user)


# -------------------------------
# ELIMINAR USUARIO (ADMIN)
# -------------------------------
@usuarios_bp.route("/eliminar/<int:user_id>")
@admin_required
def eliminar(user_id):
    db = get_db()
    db.execute("DELETE FROM usuarios WHERE id=?", (user_id,))
    db.commit()

    flash("Usuario eliminado", "success")
    return redirect(url_for("usuarios.index"))
