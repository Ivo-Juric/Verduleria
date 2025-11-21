from flask import Flask, render_template
from app.routes.productos import productos_bp
from app.routes.ventas import ventas_bp
from app.routes.reportes import reportes_bp
from app.routes.auth import auth_bp
from app.routes.usuarios import usuarios_bp
from app.routes.admin import admin_bp
from db import close_db

def create_app():
    app = Flask(__name__)
    app.secret_key = "clave-super-secreta"

    # Registrar Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(productos_bp)
    app.register_blueprint(ventas_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(usuarios_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.teardown_appcontext
    def teardown_db(exception):
        close_db()

    return app
