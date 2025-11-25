from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from flask import Blueprint, render_template, request, jsonify, send_file
import datetime, csv, io
from db import get_db
from app.utils.auth_decorators import login_required


reportes_bp = Blueprint("reportes", __name__, url_prefix="/reportes")


def _build_ventas_query(args, limit=200):
    # Leer filtros desde args
    fecha_desde = args.get("fecha_desde")
    fecha_hasta = args.get("fecha_hasta")
    prod_ids = args.getlist("producto")
    cat_ids = args.getlist("categoria")
    uni_ids = args.getlist("unidad")
    precio_min = args.get("precio_min")
    precio_max = args.get("precio_max")

    sql = "SELECT v.* FROM ventas v"
    where = []
    params = []

    # Apply filters using EXISTS on detalle_ventas/products
    if prod_ids or cat_ids or uni_ids or precio_min or precio_max:
        sql += " WHERE EXISTS (SELECT 1 FROM detalle_ventas d JOIN productos p ON d.producto_id = p.id WHERE d.venta_id = v.id"
        conds = []
        if prod_ids:
            placeholders = ",".join(["?" for _ in prod_ids])
            conds.append(f"p.id IN ({placeholders})")
            params.extend(prod_ids)
        if cat_ids:
            placeholders = ",".join(["?" for _ in cat_ids])
            conds.append(f"p.categoria_id IN ({placeholders})")
            params.extend(cat_ids)
        if uni_ids:
            placeholders = ",".join(["?" for _ in uni_ids])
            conds.append(f"p.unidad_id IN ({placeholders})")
            params.extend(uni_ids)
        # (No aplicar aquí el filtro de precio por venta; lo haremos sobre v.total más abajo)

        if conds:
            sql += " AND (" + " OR ".join(conds) + ")"
        sql += ")"

    # Date filters (fuera del EXISTS, sobre la venta)
    if fecha_desde:
        where.append("date(substr(v.fecha,1,10)) >= date(?)")
        params.append(fecha_desde)
    if fecha_hasta:
        where.append("date(substr(v.fecha,1,10)) <= date(?)")
        params.append(fecha_hasta)

    # Filtrar por total de la venta
    if precio_min:
        where.append("v.total >= ?")
        params.append(precio_min)
    if precio_max:
        where.append("v.total <= ?")
        params.append(precio_max)

    if where:
        if "WHERE EXISTS" in sql:
            sql += " AND " + " AND ".join(where)
        else:
            sql += " WHERE " + " AND ".join(where)

    sql += f" ORDER BY v.fecha DESC LIMIT {int(limit)}"

    filtros = {
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "prod_ids": prod_ids,
        "cat_ids": cat_ids,
        "uni_ids": uni_ids,
        "precio_min": precio_min,
        "precio_max": precio_max,
    }

    return sql, params, filtros


@reportes_bp.route("/")
@login_required
def index():
    db = get_db()

    # Obtener filtros posibles para el formulario
    productos = db.execute("SELECT id, nombre FROM productos ORDER BY nombre").fetchall()
    categorias = db.execute("SELECT id, nombre FROM categorias ORDER BY nombre").fetchall()
    unidades = db.execute("SELECT id, nombre FROM unidades ORDER BY nombre").fetchall()

    # Construir la consulta usando helper centralizado (respeta todos los filtros)
    sql, params, filtros = _build_ventas_query(request.args, limit=200)

    ventas = db.execute(sql, params).fetchall()
    return render_template("reportes/reportes.html", ventas=ventas,
                           productos=productos, categorias=categorias, unidades=unidades,
                           filtros=filtros)

@reportes_bp.route("/export/pdf")
@login_required
def export_pdf():
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    db = get_db()
    # Construir la misma consulta que usa la vista de reportes para respetar filtros
    sql, params, _ = _build_ventas_query(request.args, limit=1000)
    ventas = db.execute(sql, params).fetchall()

    # Memoria
    mem = io.BytesIO()
    pdf = SimpleDocTemplate(mem, pagesize=letter)

    styles = getSampleStyleSheet()
    elementos = []

    # Título
    titulo = Paragraph("<b>Reporte de Ventas</b>", styles["Title"])
    elementos.append(titulo)
    elementos.append(Spacer(1, 20))

    # Encabezados de tabla
    data = [["ID", "Fecha", "Total"]]

    # Datos
    for v in ventas:
        data.append([
            v["id"],
            v["fecha"],
            f"${v['total']}"
        ])

    # Tabla
    tabla = Table(data, colWidths=[60, 200, 100])

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),

        # Bordes
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elementos.append(tabla)

    # Generar PDF
    pdf.build(elementos)
    mem.seek(0)

    return send_file(mem, download_name="reporte.pdf", as_attachment=True)

@reportes_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("reportes/dashboard.html")


@reportes_bp.route("/venta/<int:id>")
@login_required
def ver_venta(id):
    db = get_db()
    venta = db.execute("SELECT * FROM ventas WHERE id=?", (id,)).fetchone()
    if not venta:
        from flask import flash, redirect, url_for
        flash("Venta no encontrada", "danger")
        return redirect(url_for("reportes.index"))

    detalles = db.execute("""
        SELECT d.*, p.nombre, u.nombre as unidad
        FROM detalle_ventas d
        JOIN productos p ON d.producto_id = p.id
        LEFT JOIN unidades u ON p.unidad_id = u.id
        WHERE d.venta_id = ?
    """, (id,)).fetchall()

    # Crear descripción breve
    descripcion = ", ".join([f"{r['nombre']} x{r['cantidad']}" for r in detalles])

    return render_template("reportes/ver_venta.html", venta=venta, detalles=detalles, descripcion=descripcion)


@reportes_bp.route("/venta/<int:id>/pdf")
@login_required
def venta_pdf(id):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    db = get_db()
    venta = db.execute("SELECT * FROM ventas WHERE id=?", (id,)).fetchone()
    if not venta:
        from flask import flash, redirect, url_for
        flash("Venta no encontrada", "danger")
        return redirect(url_for("reportes.index"))

    detalles = db.execute("""
        SELECT d.*, p.nombre
        FROM detalle_ventas d
        JOIN productos p ON d.producto_id = p.id
        WHERE d.venta_id = ?
    """, (id,)).fetchall()

    descripcion = ", ".join([f"{r['nombre']} x{r['cantidad']}" for r in detalles])

    mem = io.BytesIO()
    pdf = SimpleDocTemplate(mem, pagesize=letter)
    styles = getSampleStyleSheet()
    elems = []
    elems.append(Paragraph(f"Venta ID: {venta['id']}", styles['Heading2']))
    elems.append(Paragraph(f"Fecha: {venta['fecha']}", styles['Normal']))
    elems.append(Spacer(1, 12))
    elems.append(Paragraph(f"Total: ${venta['total']}", styles['Normal']))
    elems.append(Spacer(1, 12))
    elems.append(Paragraph(f"Descripción: {descripcion}", styles['Normal']))
    pdf.build(elems)
    mem.seek(0)
    return send_file(mem, download_name=f"venta_{venta['id']}.pdf", as_attachment=True)

@reportes_bp.route("/data")
@login_required
def data():
    db = get_db()

    ventas = db.execute("""
        SELECT substr(fecha,1,10) AS dia, SUM(total) AS total
        FROM ventas
        GROUP BY dia
        ORDER BY dia ASC
    """).fetchall()

    top = db.execute("""
        SELECT p.nombre, SUM(d.cantidad) AS cantidad
        FROM detalle_ventas d
        JOIN productos p ON d.producto_id=p.id
        GROUP BY p.id
        ORDER BY cantidad DESC
        LIMIT 7
    """).fetchall()

    return jsonify({
        "ventas": [{"dia": r["dia"], "total": r["total"]} for r in ventas],
        "top": [{"nombre": t["nombre"], "cantidad": t["cantidad"]} for t in top]
    })


@reportes_bp.route("/ganancias_netas")
@login_required
def ganancias_netas():
    """
    Calcula ganancias netas diarias: total de ventas - costo total.
    El costo se estima como: suma de (cantidad * precio_unitario_ingreso) para cada producto vendido.
    """
    db = get_db()

    # Obtener ventas diarias y sus costos
    resultado = db.execute("""
        SELECT
            substr(v.fecha,1,10) AS dia,
            SUM(v.total) AS venta_total,
            COALESCE(SUM(d.cantidad * COALESCE((
                SELECT AVG(i.precio_unitario)
                FROM ingresos_stock i
                WHERE i.producto_id = d.producto_id
            ), 0)), 0) AS costo_total
        FROM ventas v
        LEFT JOIN detalle_ventas d ON v.id = d.venta_id
        GROUP BY dia
        ORDER BY dia ASC
    """).fetchall()

    data_list = []
    for r in resultado:
        ganancia = float(r["venta_total"] or 0) - float(r["costo_total"] or 0)
        data_list.append({
            "dia": r["dia"],
            "venta": float(r["venta_total"] or 0),
            "costo": float(r["costo_total"] or 0),
            "ganancia": ganancia
        })

    return jsonify(data_list)


@reportes_bp.route("/top_proveedores")
@login_required
def top_proveedores():
    """
    Retorna top 10 proveedores más baratos por producto.
    Ordena por precio unitario promedio ascendente.
    """
    db = get_db()

    resultado = db.execute("""
        SELECT
            pr.id,
            pr.nombre,
            COUNT(DISTINCT i.producto_id) AS cantidad_productos,
            AVG(i.precio_unitario) AS precio_promedio
        FROM proveedores pr
        LEFT JOIN ingresos_stock i ON pr.id = i.proveedor_id
        GROUP BY pr.id, pr.nombre
        ORDER BY precio_promedio ASC
        LIMIT 10
    """).fetchall()

    data_list = [
        {
            "nombre": r["nombre"],
            "cantidad_productos": r["cantidad_productos"],
            "precio_promedio": float(r["precio_promedio"] or 0)
        }
        for r in resultado
    ]

    return jsonify(data_list)
