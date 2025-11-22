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

    # Buscar productos existentes
    productos = db.execute("SELECT id, precio FROM productos").fetchall()
    if len(productos) == 0:
        return "Primero cargá productos con /admin/cargar_test"

    # Crear una venta
    db.execute(
        "INSERT INTO ventas (fecha, total) VALUES (datetime('now'), 0)"
    )
    venta_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    total_venta = 0

    # Crear detalles de venta (random de 2 productos)
    detalles = []
    for p in productos[:2]:  # los primeros 2 productos
        cantidad = 3
        subtotal = p["precio"] * cantidad
        total_venta += subtotal
        detalles.append((venta_id, p["id"], cantidad, subtotal))

    db.executemany("""
        INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, subtotal)
        VALUES (?, ?, ?, ?)
    """, detalles)

    # Actualizar total de la venta
    db.execute("UPDATE ventas SET total = ? WHERE id = ?", (total_venta, venta_id))

    db.commit()
    return f"Venta de prueba creada (ID: {venta_id})"
