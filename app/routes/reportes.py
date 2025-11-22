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

@reportes_bp.route("/export/csv")
@login_required
def export_csv():
    db = get_db()
    rows = db.execute("""
        SELECT v.id, v.fecha, v.total, d.producto_id, d.cantidad, d.subtotal
        FROM ventas v
        JOIN detalle_venta d ON v.id=d.venta_id
    """).fetchall()

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(["venta_id", "fecha", "total", "producto_id", "cantidad", "subtotal"])

    for r in rows:
        cw.writerow([r["id"], r["fecha"], r["total"],
                     r["producto_id"], r["cantidad"], r["subtotal"]])

    mem = io.BytesIO()
    mem.write(si.getvalue().encode("utf-8"))
    mem.seek(0)

    return send_file(mem, download_name="reporte.csv", as_attachment=True)

@reportes_bp.route("/export/pdf")
@login_required
def export_pdf():
    db = get_db()
    ventas = db.execute("SELECT * FROM ventas ORDER BY fecha DESC LIMIT 100").fetchall()

    mem = io.BytesIO()
    c = canvas.Canvas(mem, pagesize=letter)
    y = 750
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Reporte de ventas")
    c.setFont("Helvetica", 10)
    y -= 40

    for v in ventas:
        c.drawString(40, y, f"ID:{v['id']}  Fecha:{v['fecha']}  Total:${v['total']}")
        y -= 20
        if y < 40:
            c.showPage()
            y = 750

    c.save()
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
