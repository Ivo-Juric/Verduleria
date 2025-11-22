from flask import Blueprint, render_template
from db import get_db
from app.utils.auth_decorators import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# --------------------------
# RUTA PRINCIPAL DEL ADMIN
# --------------------------

@admin_bp.route("/")
@admin_required
def admin_home():
    # Carga automática al ingresar como admin
    cargar_test()
    cargar_test_ventas()

    return render_template("admin/index.html")


@admin_bp.route("/usuarios")
@admin_required
def users():
    db = get_db()
    lista = db.execute("SELECT id, username, role FROM usuarios").fetchall()
    return render_template("usuarios/index.html", usuarios=lista)
