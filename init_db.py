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

    # Crear usuario admin si no existe
    cursor.execute("SELECT * FROM usuarios WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO usuarios (username, password_hash, role)
            VALUES (?, ?, ?)
        """, ("admin", hash_pass("admin123"), "admin"))
        print("Usuario admin creado: admin / admin123")

    # -----------------------
    # Tabla categorías
    # -----------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categorias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE
    );
    """)

    cursor.executemany("""
        INSERT OR IGNORE INTO categorias (nombre)
        VALUES (?)
    """, [
        ("Frutas",),
        ("Verduras",),
        ("Tubérculos",),
        ("Hoja Verde",)
    ])

    # -----------------------
    # Tabla unidades
    # -----------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS unidades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE
    );
    """)

    cursor.executemany("""
        INSERT OR IGNORE INTO unidades (nombre)
        VALUES (?)
    """, [
        ("Kg",),
        ("Unidad",),
        ("Paquete",)
    ])

    # -----------------------
    # Tabla productos
    # -----------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        precio REAL NOT NULL,
        stock INTEGER NOT NULL DEFAULT 0,
        categoria_id INTEGER,
        unidad_id INTEGER,
        FOREIGN KEY (categoria_id) REFERENCES categorias(id),
        FOREIGN KEY (unidad_id) REFERENCES unidades(id)
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
    # Tabla detalle ventas
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

    # -----------------------
    # Tabla proveedores
    # -----------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proveedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        contacto TEXT,
        telefono TEXT,
        email TEXT
    );
    """)

    # -----------------------
    # Tabla ingresos de stock
    # -----------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ingresos_stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producto_id INTEGER NOT NULL,
        proveedor_id INTEGER NOT NULL,
        cantidad REAL NOT NULL,
        fecha TEXT NOT NULL,
        precio_unitario REAL,
        FOREIGN KEY (producto_id) REFERENCES productos(id),
        FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
    );
    """)

    # -----------------------
    # Cargar proveedores de prueba
    # -----------------------
    cursor.execute("SELECT COUNT(*) FROM proveedores")
    if cursor.fetchone()[0] == 0:
        print("Cargando proveedores de prueba...")
        cursor.executemany("""
            INSERT INTO proveedores (nombre, contacto, telefono, email)
            VALUES (?, ?, ?, ?)
        """, [
            ("Agrofresco SA", "Juan Pérez", "011-1234-5678", "juan@agrofresco.com"),
            ("Verduras del Sur", "María García", "011-8765-4321", "maria@verdurassur.com"),
            ("Distribuidora Central", "Carlos López", "011-5555-5555", "carlos@distcentral.com")
        ])

    # -----------------------
    # CARGA AUTOMÁTICA DE PRODUCTOS DE PRUEBA SOLO SI LA TABLA ESTÁ VACÍA
    # -----------------------
    cursor.execute("SELECT COUNT(*) FROM productos")
    if cursor.fetchone()[0] == 0:
        print("Cargando productos de prueba...")
        cursor.executemany("""
            INSERT INTO productos (nombre, precio, stock, categoria_id, unidad_id)
            VALUES (?, ?, ?, ?, ?)
        """, [
            ("Manzana Roja", 800, 50, 1, 1),
            ("Banana Ecuador", 600, 80, 1, 1),
            ("Naranja Jugosa", 400, 100, 1, 1),
            ("Papa Blanca", 300, 120, 3, 1),
            ("Lechuga Crespa", 500, 40, 4, 2)
        ])

    # --------------------------------------------------------------
    # CARGA DE VENTAS DE PRUEBA (solo si no existen)
    # --------------------------------------------------------------
    cursor.execute("SELECT COUNT(*) FROM ventas")
    if cursor.fetchone()[0] == 0:
        print("Cargando ventas de prueba...")

        ventas = [
            ("2025-01-10", 5600),
            ("2025-01-11", 3200),
            ("2025-01-12", 8900),
            ("2025-01-13", 4500),
            ("2025-01-14", 12000)
        ]

        cursor.executemany("INSERT INTO ventas (fecha, total) VALUES (?, ?)", ventas)

        # Obtener IDs recién insertados
        cursor.execute("SELECT id FROM ventas ORDER BY id ASC")
        ventas_ids = [x[0] for x in cursor.fetchall()]

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

        cursor.executemany("""
            INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, subtotal)
            VALUES (?, ?, ?, ?)
        """, detalle)

    conn.commit()
    conn.close()
    print("Base de datos creada con datos de ejemplo.")

if __name__ == "__main__":
    init_db()
