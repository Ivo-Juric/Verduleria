from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from flask import Blueprint, render_template, request, jsonify, send_file
import datetime, csv, io
from db import get_db
from app.utils.auth_decorators import login_required


reportes_bp = Blueprint("reportes", __name__, url_prefix="/reportes")

@reportes_bp.route("/")
@login_required
def index():
    db = get_db()
    ventas = db.execute("SELECT * FROM ventas ORDER BY fecha DESC LIMIT 50").fetchall()
    return render_template("reportes/reportes.html", ventas=ventas)

@reportes_bp.route("/export/pdf")
@login_required
def export_pdf():
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    db = get_db()
    ventas = db.execute("""
        SELECT id, fecha, total
        FROM ventas
        ORDER BY fecha DESC LIMIT 100
    """).fetchall()

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
