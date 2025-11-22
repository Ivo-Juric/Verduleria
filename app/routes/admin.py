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


@admin_bp.route("/cargar_test")
@admin_required
def cargar_test():
    db = get_db()

    productos = [
        ("Manzana Roja", 800, 50, 1, 1),   # Frutas - Kg
        ("Banana Ecuador", 600, 80, 1, 1), # Frutas - Kg
        ("Naranja Jugosa", 400, 100, 1, 1),
        ("Papa Blanca", 300, 120, 3, 1),   # Tubérculos - Kg
        ("Lechuga Crespa", 500, 40, 4, 2)  # Hoja verde - Unidad
    ]

    db.executemany("""
        INSERT INTO productos (nombre, precio, stock, categoria_id, unidad_id)
        VALUES (?, ?, ?, ?, ?)
    """, productos)

    db.commit()
    return "Productos de prueba cargados correctamente"


@admin_bp.route("/cargar_test_ventas")
@admin_required
def cargar_test_ventas():
    db = get_db()

    ventas = [
        ("2025-01-10", 5600),
        ("2025-01-11", 3200),
        ("2025-01-12", 8900),
        ("2025-01-13", 4500),
        ("2025-01-14", 12000)
    ]

    db.executemany("INSERT INTO ventas (fecha, total) VALUES (?, ?)", ventas)

    ventas_ids = db.execute(
        "SELECT id FROM ventas ORDER BY id DESC LIMIT 5"
    ).fetchall()

    ventas_ids = [v["id"] for v in ventas_ids][::-1]

    detalle = [
        (ventas_ids[0], 1, 3, 2400),
        (ventas_ids[0], 2, 2, 1200),
        (ventas_ids[0], 3, 2, 1000),

        (ventas_ids[1], 4, 5, 1500),
        (ventas_ids[1], 5, 2, 1000),

        (ventas_ids[2], 1, 5, 4000),
        (ventas_ids[2], 2, 6, 3600),
        (ventas_ids[2], 3, 3, 1300),

        (ventas_ids[3], 4, 4, 1200),
        (ventas_ids[3], 1, 3, 2400),
        (ventas_ids[3], 5, 1, 500),

        (ventas_ids[4], 2, 10, 6000),
        (ventas_ids[4], 3, 10, 4000),
        (ventas_ids[4], 4, 8, 2000)
    ]

    db.executemany("""
        INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, subtotal)
        VALUES (?, ?, ?, ?)
    """, detalle)

    db.commit()
    return "Ventas de prueba cargadas correctamente"
