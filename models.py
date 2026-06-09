"""
Database Models untuk Dapur Hijrah (Es Teler App)
Sesuai SDD: 7 tabel utama (users, menus, orders, order_items, carts, cart_items, recommendations)

PERUBAHAN dari versi lama:
- User extend UserMixin (FIX: Flask-Login crash)
- Tambah kolom sesuai SDD: payment_method, order_source, expires_at, is_favorite, updated_at, added_at
- Tambah INDEX di kolom yang sering di-query (performa lebih cepat)
- Tambah method helper: User.set_password(), User.check_password(), Order.calculate_total()
- Pakai datetime.now(timezone.utc) (datetime.utcnow sudah deprecated di Python 3.12+)
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, timedelta
from sqlalchemy import Index

db = SQLAlchemy()


def now_utc():
    """Timezone-aware UTC datetime (replacement untuk datetime.utcnow)."""
    return datetime.now(timezone.utc)


# =============================================================================
# 1. USERS (Admin/Penjual saja - customer tidak login)
# =============================================================================
class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    # Default role 'admin' karena tabel ini hanya untuk admin (sesuai SDD)
    role = db.Column(db.String(20), default="admin", nullable=False)
    avatar_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True), default=now_utc)

    def set_password(self, password: str) -> None:
        """Hash password sebelum disimpan."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verifikasi password input dengan hash di DB."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "avatar_url": self.avatar_url,
        }


# =============================================================================
# 2. MENUS
# =============================================================================
class Menu(db.Model):
    __tablename__ = "menus"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    price = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(255))
    category = db.Column(db.String(50), index=True)
    rating = db.Column(db.Float, default=0.0)
    sold_count = db.Column(db.Integer, default=0, index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_best_seller = db.Column(db.Boolean, default=False, index=True)
    is_favorite = db.Column(db.Boolean, default=False)  # NEW - sesuai SDD
    created_at = db.Column(db.DateTime(timezone=True), default=now_utc)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=now_utc, onupdate=now_utc
    )  # NEW - sesuai SDD

    # Composite index untuk query yang sering dilakukan customer
    __table_args__ = (Index("idx_menu_active_category", "is_active", "category"),)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "image_url": self.image_url,
            "category": self.category,
            "rating": self.rating,
            "sold_count": self.sold_count,
            "is_active": self.is_active,
            "is_best_seller": self.is_best_seller,
            "is_favorite": self.is_favorite,
        }


# =============================================================================
# 3. CARTS (session-based, no login)
# =============================================================================
class Cart(db.Model):
    __tablename__ = "carts"

    id = db.Column(db.Integer, primary_key=True)
    # Index untuk lookup cart by session (paling sering di-query)
    session_id = db.Column(db.String(100), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=now_utc)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=now_utc, onupdate=now_utc
    )

    items = db.relationship(
        "CartItem",
        backref="cart",
        lazy="select",  # Default lazy loading
        cascade="all, delete-orphan",
    )


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(
        db.Integer, db.ForeignKey("carts.id"), nullable=False, index=True
    )
    menu_id = db.Column(
        db.Integer, db.ForeignKey("menus.id"), nullable=False, index=True
    )
    quantity = db.Column(db.Integer, default=1, nullable=False)
    added_at = db.Column(
        db.DateTime(timezone=True), default=now_utc
    )  # NEW - sesuai SDD

    # Relasi ke Menu agar bisa eager-load (FIX: N+1 query problem)
    menu = db.relationship("Menu", lazy="joined")


# =============================================================================
# 4. ORDERS
# =============================================================================
class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    # Index karena customer tracking pakai order_code
    order_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    customer_name = db.Column(db.String(100))
    customer_contact = db.Column(db.String(50))  # NEW - butuh untuk kontak
    pickup_schedule = db.Column(db.DateTime(timezone=True))
    note = db.Column(db.Text)
    status = db.Column(db.String(20), default="menunggu", nullable=False, index=True)
    # NEW sesuai SDD revisi: payment_method (QRIS/TUNAI/COD)
    payment_method = db.Column(db.String(20), default="TUNAI", nullable=False)
    # NEW sesuai SDD revisi: order_source (ONLINE_PREORDER/WALKIN)
    order_source = db.Column(
        db.String(20), default="ONLINE_PREORDER", nullable=False, index=True
    )
    total = db.Column(db.Integer, nullable=False)
    order_type = db.Column(db.String(20), default="pickup")  # pickup/delivery/dine-in
    rating = db.Column(db.Integer, nullable=True)  # NEW - rating pesanan
    created_at = db.Column(db.DateTime(timezone=True), default=now_utc, index=True)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=now_utc, onupdate=now_utc
    )  # NEW - sesuai SDD

    items = db.relationship(
        "OrderItem", backref="order", lazy="select", cascade="all, delete-orphan"
    )

    def calculate_total(self):
        """Hitung ulang total dari order_items (untuk validasi)."""
        return sum(item.subtotal for item in self.items)

    def to_dict(self):
        return {
            "id": self.id,
            "order_code": self.order_code,
            "customer_name": self.customer_name,
            "status": self.status,
            "payment_method": self.payment_method,
            "order_source": self.order_source,
            "total": self.total,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "items": [item.to_dict() for item in self.items],
        }


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True
    )
    menu_id = db.Column(
        db.Integer, db.ForeignKey("menus.id"), nullable=False, index=True
    )
    quantity = db.Column(db.Integer, nullable=False)
    # Snapshot harga saat order (penting untuk integritas data historis)
    price_at_order = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Integer, nullable=False)

    menu = db.relationship("Menu", lazy="joined")

    def to_dict(self):
        return {
            "menu_id": self.menu_id,
            "menu_name": self.menu.name if self.menu else None,
            "quantity": self.quantity,
            "price_at_order": self.price_at_order,
            "subtotal": self.subtotal,
        }


# =============================================================================
# 5. RECOMMENDATIONS (cache hasil AI)
# =============================================================================
class Recommendation(db.Model):
    __tablename__ = "recommendations"

    id = db.Column(db.Integer, primary_key=True)
    menu_id = db.Column(
        db.Integer, db.ForeignKey("menus.id"), nullable=False, index=True
    )
    session_id = db.Column(db.String(100), nullable=False, index=True)
    match_score = db.Column(db.Float)
    reason = db.Column(db.String(255))
    generated_at = db.Column(db.DateTime(timezone=True), default=now_utc)
    # NEW sesuai SDD: expires_at untuk cache invalidation
    expires_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: now_utc() + timedelta(hours=1),
        index=True,
    )

    menu = db.relationship("Menu", lazy="joined")

    # Composite index untuk query cache lookup: WHERE session_id=? AND expires_at>?
    __table_args__ = (Index("idx_reco_session_expiry", "session_id", "expires_at"),)

    def to_dict(self):
        return {
            "menu_id": self.menu_id,
            "menu": self.menu.to_dict() if self.menu else None,
            "match_score": self.match_score,
            "reason": self.reason,
        }
