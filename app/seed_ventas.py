import sqlite3
from datetime import datetime

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Crear una venta
fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
total = 3500

cursor.execute(
    "INSERT INTO ventas (fecha, total) VALUES (?, ?)",
    (fecha, total)
)

venta_id = cursor.lastrowid

# Detalle de esa venta
items = [
    (venta_id, 1, 2, 2400),  # 2 Manzanas
    (venta_id, 4, 1, 800),   # 1 Tomate
    (venta_id, 5, 1, 300)    # 1 Papa
]

cursor.executemany(
    "INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, subtotal) VALUES (?, ?, ?, ?)",
    items
)

conn.commit()
conn.close()

print("Venta y detalles cargados!")
