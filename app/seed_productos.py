import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

productos = [
    ("Manzana Roja", 1200, 50),
    ("Banana Ecuador", 900, 80),
    ("Pera Williams", 1300, 40),
    ("Tomate", 800, 100),
    ("Papa Negra", 500, 200)
]

cursor.executemany(
    "INSERT INTO productos(nombre, precio, stock) VALUES (?, ?, ?)",
    productos
)

conn.commit()
conn.close()

print("Productos de prueba cargados!")
