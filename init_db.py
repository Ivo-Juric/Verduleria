import sqlite3
import hashlib

DB_NAME = "database.db"

def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # -----------------------
    # Tabla usuarios
    # -----------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user'
    );
    """)

    # Crear usuario admin por defecto
    cursor.execute("""
    SELECT * FROM usuarios WHERE username = 'admin';
    """)
    admin = cursor.fetchone()

    if not admin:
        cursor.execute("""
        INSERT INTO usuarios(username, password_hash, role)
        VALUES (?, ?, ?)
        """, ("admin", hash_pass("admin123"), "admin"))
        print("Usuario admin creado: admin / admin123")

    # -----------------------
    # Tabla productos
    # -----------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        precio REAL NOT NULL,
        stock INTEGER NOT NULL DEFAULT 0
    );
    """)

    # -----------------------
    # Tabla ventas
    # -----------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        total REAL NOT NULL
    );
    """)

    # -----------------------
    # Detalle de ventas
    # -----------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS detalle_ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venta_id INTEGER NOT NULL,
        producto_id INTEGER NOT NULL,
        cantidad INTEGER NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY (venta_id) REFERENCES ventas(id),
        FOREIGN KEY (producto_id) REFERENCES productos(id)
    );
    """)

    conn.commit()
    conn.close()
    print("Base de datos creada correctamente.")


if __name__ == "__main__":
    init_db()
