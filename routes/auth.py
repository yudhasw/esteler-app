"""
Routes Auth - login/logout admin
"""
from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import login_user, logout_user, login_required, current_user
from services.auth_service import AuthService

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Kalau sudah login, langsung redirect ke dashboard
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        if not username or not password:
            flash("Username dan password wajib diisi.", "danger")
            return render_template("auth/login.html")

        user = AuthService.login(username, password)
        if user:
            login_user(user, remember=remember)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("admin.dashboard"))

        flash("Username atau password salah.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Anda telah keluar.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot", methods=["GET", "POST"])
def forgot_password():
    """Stub - implementasi reset password via email belum dibuat."""
    if request.method == "POST":
        flash("Fitur reset password belum tersedia. Hubungi admin.", "warning")
    return render_template("auth/forgot.html")
