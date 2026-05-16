"""
Routes Customer - sisi pembeli (TANPA login)
Identifikasi pakai session_id di cookie.
"""
import uuid
from flask import (
    Blueprint, request, redirect, url_for, session, render_template, flash, abort,
)

from services.menu_service import MenuService
from services.cart_service import CartService
from services.order_service import OrderService
from services.recommendation_service import RecommendationService

customer_bp = Blueprint("customer", __name__)


def get_session_id() -> str:
    """Ambil/buat session_id untuk identifikasi customer anonim."""
    if "cart_session_id" not in session:
        session["cart_session_id"] = str(uuid.uuid4())
        session.permanent = True  # Pakai PERMANENT_SESSION_LIFETIME dari config
    return session["cart_session_id"]


# ====================== HOME & MENU ======================
@customer_bp.route("/")
def home():
    best_sellers = MenuService.get_best_sellers(limit=5)
    return render_template("customer/home.html", best_sellers=best_sellers)


@customer_bp.route("/menu")
def menu_list():
    keyword = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    if keyword:
        menus = MenuService.search(keyword)
    elif category:
        menus = MenuService.get_by_category(category)
    else:
        menus = MenuService.get_all(active_only=True)

    # Rekomendasi untuk carousel di atas
    recommendations = RecommendationService.get_recommendations(
        get_session_id(), limit=3
    )

    # Cart count untuk floating button
    cart_summary = CartService.get_summary(get_session_id())

    return render_template(
        "customer/menu.html",
        menus=menus,
        recommendations=recommendations,
        cart_count=cart_summary["total_items"],
        active_category=category,
        keyword=keyword,
    )


# ====================== CART ======================
@customer_bp.route("/cart")
def cart_view():
    summary = CartService.get_summary(get_session_id())
    return render_template("customer/cart.html", summary=summary)


@customer_bp.route("/cart/add", methods=["POST"])
def add_to_cart():
    try:
        menu_id = int(request.form.get("menu_id", 0))
        quantity = int(request.form.get("quantity", 1))
        CartService.add_item(get_session_id(), menu_id, quantity)
        flash("Ditambahkan ke keranjang.", "success")
    except (ValueError, TypeError) as e:
        flash(str(e), "danger")
    return redirect(request.referrer or url_for("customer.menu_list"))


@customer_bp.route("/cart/update/<int:item_id>", methods=["POST"])
def update_cart(item_id):
    try:
        qty = int(request.form.get("quantity", 0))
        CartService.update_quantity(item_id, qty)
    except (ValueError, TypeError):
        flash("Quantity tidak valid.", "danger")
    return redirect(url_for("customer.cart_view"))


@customer_bp.route("/cart/remove/<int:item_id>", methods=["POST"])
def remove_from_cart(item_id):
    CartService.remove_item(item_id)
    flash("Item dihapus dari keranjang.", "info")
    return redirect(url_for("customer.cart_view"))


# ====================== PREORDER / CHECKOUT ======================
@customer_bp.route("/preorder", methods=["GET", "POST"])
def preorder():
    session_id = get_session_id()

    if request.method == "POST":
        customer_data = {
            "name": request.form.get("customer_name", "").strip(),
            "contact": request.form.get("customer_contact", "").strip(),
            "pickup_schedule": request.form.get("pickup_schedule"),
            "note": request.form.get("note", "").strip(),
            "order_type": request.form.get("order_type", "pickup"),
            "payment_method": request.form.get("payment_method", "TUNAI"),
        }

        if not customer_data["name"]:
            flash("Nama wajib diisi.", "danger")
        else:
            try:
                order = OrderService.create_order(session_id, customer_data)
                if order:
                    return redirect(
                        url_for("customer.track_status", code=order.order_code)
                    )
                flash("Keranjang kosong atau tidak valid.", "danger")
            except Exception as e:
                flash(f"Gagal membuat pesanan: {e}", "danger")

    summary = CartService.get_summary(session_id)
    if summary["is_empty"]:
        flash("Keranjang Anda kosong.", "info")
        return redirect(url_for("customer.menu_list"))

    return render_template("customer/preorder.html", summary=summary)


# ====================== TRACKING ======================
@customer_bp.route("/track")
def track_form():
    """Form input order code."""
    code = request.args.get("code", "").strip()
    if code:
        return redirect(url_for("customer.track_status", code=code))
    return render_template("customer/track_form.html")


@customer_bp.route("/track/<code>")
def track_status(code):
    order = OrderService.get_by_code(code)
    if not order:
        flash("Pesanan tidak ditemukan.", "danger")
        return redirect(url_for("customer.track_form"))
    return render_template("customer/track_status.html", order=order)
