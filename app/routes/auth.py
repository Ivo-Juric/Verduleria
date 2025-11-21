from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_db, hash_pass
from app.utils.auth_decorators import login_required, admin_required
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        db = get_db()

        user = db.execute("SELECT * FROM usuarios WHERE username=?", (u,)).fetchone()

        if user and user["password_hash"] == hash_pass(p):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect("/")

        flash("Usuario o contraseña incorrectos", "danger")

    return render_template("auth/login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@auth_bp.route("/register", methods=["GET", "POST"])
@admin_required
def register():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        r = request.form.get("role", "user")

        db = get_db()
        try:
            db.execute("INSERT INTO usuarios(username, password_hash, role) VALUES (?, ?, ?)",
                       (u, hash_pass(p), r))
            db.commit()
            flash("Usuario creado correctamente", "success")
            return redirect(url_for("admin.users"))
        except Exception as e:
            flash("Error: ese usuario ya existe", "danger")

    return render_template("auth/register.html")
