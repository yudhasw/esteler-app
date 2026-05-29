"""
Entry point untuk Vercel Serverless Function.

Struktur ini SPECIFIC untuk Vercel:
- File harus di folder api/
- Harus expose variable bernama `app`
- Path templates/static di-set eksplisit karena beda folder

Untuk lokal: pakai `python app.py` di root (bukan file ini).
"""

import os
import sys

# Tambah parent directory ke path agar bisa import modul dari root project
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from flask import Flask, session
from flask_login import LoginManager
from flask_migrate import Migrate
from dotenv import load_dotenv

load_dotenv()

from config import Config
from models import db, User
from routes.customer import customer_bp
from routes.admin import admin_bp
from routes.auth import auth_bp


def create_app() -> Flask:
    # Path eksplisit karena file ini di api/, sementara templates/ di root
    template_dir = os.path.join(ROOT_DIR, "templates")
    static_dir = os.path.join(ROOT_DIR, "static")

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config.from_object(Config)

    # Inisialisasi extensions
    db.init_app(app)
    Migrate(app, db)

    # Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Silakan login terlebih dahulu."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    app.register_blueprint(customer_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)

    # Context processor: cart_count otomatis tersedia di semua template
    @app.context_processor
    def inject_cart_count():
        from services.cart_service import CartService
        session_id = session.get("cart_session_id")
        count = 0
        if session_id:
            try:
                count = CartService.get_summary(session_id)["total_items"]
            except Exception:
                count = 0
        return {"cart_count": count}

    # Global template context (currency formatter dll)
    @app.template_filter("rupiah")
    def format_rupiah(value):
        if value is None:
            return "Rp0"
        return f"Rp{int(value):,}".replace(",", ".")

    @app.template_filter("status_color")
    def status_color(status):
        """Mapping status order ke warna badge."""
        return {
            "menunggu": "amber",
            "memasak": "blue",
            "siap": "purple",
            "selesai": "green",
            "dibatalkan": "red",
        }.get(status, "gray")

    return app


app = create_app()


# Untuk testing lokal - jangan dipakai di Vercel
if __name__ == "__main__":
    app.run(debug=True, port=5000)