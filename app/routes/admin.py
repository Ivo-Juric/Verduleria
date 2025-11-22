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

    # ---- Productos de prueba ----
    productos = [
        ("Manzana Roja", 800, 50),
        ("Banana Ecuador", 600, 80),
        ("Naranja Jugosa", 400, 100),
        ("Papa Blanca", 300, 120),
        ("Lechuga Crespa", 500, 40)
    ]

    db.executemany(
        "INSERT INTO productos (nombre, precio, stock) VALUES (?, ?, ?)",
        productos
    )

    db.commit()
    return "Productos de prueba cargados correctamente"

@admin_bp.route("/cargar_test_ventas")
@admin_required
def cargar_test_ventas():
    db = get_db()

    # Crear 5 ventas de prueba
    ventas = [
        ("2025-01-10", 5600),
        ("2025-01-11", 3200),
        ("2025-01-12", 8900),
        ("2025-01-13", 4500),
        ("2025-01-14", 12000)
    ]
    db.executemany("INSERT INTO ventas (fecha, total) VALUES (?, ?)", ventas)

    # Obtener IDs reales de las ventas insertadas
    ventas_ids = db.execute("SELECT id FROM ventas ORDER BY id DESC LIMIT 5").fetchall()
    ventas_ids = [v["id"] for v in ventas_ids][::-1]  # ordenar cronológicamente

    # Detalle de ventas basado en los productos que cargaste
    detalle = [
        # Venta 1
        (ventas_ids[0], 1, 3, 2400),  # Manzana Roja
        (ventas_ids[0], 2, 2, 1200),  # Banana Ecuador
        (ventas_ids[0], 3, 2, 1000),  # Naranja

        # Venta 2
        (ventas_ids[1], 4, 5, 1500),  # Papa Blanca
        (ventas_ids[1], 5, 2, 1000),  # Lechuga

        # Venta 3
        (ventas_ids[2], 1, 5, 4000),
        (ventas_ids[2], 2, 6, 3600),
        (ventas_ids[2], 3, 3, 1300),

        # Venta 4
        (ventas_ids[3], 4, 4, 1200),
        (ventas_ids[3], 1, 3, 2400),
        (ventas_ids[3], 5, 1, 500),

        # Venta 5 (venta grande)
        (ventas_ids[4], 2, 10, 6000),
        (ventas_ids[4], 3, 10, 4000),
        (ventas_ids[4], 4, 8, 2000)
    ]

    db.executemany(
        "INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, subtotal) VALUES (?, ?, ?, ?)",
        detalle
    )

    db.commit()
    return "Ventas de prueba cargadas correctamente"
