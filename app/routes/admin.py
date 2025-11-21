from flask import Blueprint, render_template
from db import get_db
from app.utils.auth_decorators import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/usuarios")
@admin_required
def users():
    db = get_db()
    lista = db.execute("SELECT id, username, role FROM usuarios").fetchall()
    return render_template("usuarios/index.html", usuarios=lista)
