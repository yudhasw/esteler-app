"""
OrderService - lifecycle pesanan

PERUBAHAN dari versi lama:
- Support payment_method (QRIS/TUNAI/COD) - sesuai SDD revisi
- Support order_source (ONLINE_PREORDER/WALKIN) - sesuai SDD revisi
- Support create_walkin() untuk admin input manual customer offline
- generate_code(): format ORD-YYYYMMDD-XXXX (sesuai SDD)
- Eager load items+menu untuk hindari N+1
- Transactional dengan rollback kalau ada error
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from models import db, Order, OrderItem, Menu
from services.cart_service import CartService


VALID_STATUSES = {"menunggu", "memasak", "siap", "selesai", "dibatalkan"}
VALID_PAYMENTS = {"QRIS", "TUNAI", "COD"}


class OrderService:

    @staticmethod
    def generate_code() -> str:
        """Format: ORD-YYYYMMDD-XXXX (sesuai SDD)."""
        date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
        random_part = uuid.uuid4().hex[:4].upper()
        return f"ORD-{date_part}-{random_part}"

    @staticmethod
    def create_order(session_id: str, customer_data: dict) -> Optional[Order]:
        """
        Buat order baru dari isi cart (ONLINE_PREORDER).
        Transactional: rollback kalau ada error di tengah proses.
        """
        cart = CartService.get_cart_with_items(session_id)
        if not cart or not cart.items:
            return None

        payment_method = customer_data.get("payment_method", "TUNAI").upper()
        if payment_method not in VALID_PAYMENTS:
            payment_method = "TUNAI"

        # Parse pickup_schedule jika ada
        pickup_schedule = customer_data.get("pickup_schedule")
        if isinstance(pickup_schedule, str) and pickup_schedule:
            try:
                pickup_schedule = datetime.fromisoformat(pickup_schedule)
            except ValueError:
                pickup_schedule = None

        try:
            # Hitung total
            total = 0
            order_items_data = []
            for item in cart.items:
                if not item.menu or not item.menu.is_active:
                    continue
                subtotal = item.menu.price * item.quantity
                total += subtotal
                order_items_data.append({
                    "menu_id": item.menu.id,
                    "quantity": item.quantity,
                    "price_at_order": item.menu.price,
                    "subtotal": subtotal,
                })

            if total == 0:
                return None

            # Create order
            new_order = Order(
                order_code=OrderService.generate_code(),
                customer_name=customer_data.get("name", "Pelanggan"),
                customer_contact=customer_data.get("contact"),
                pickup_schedule=pickup_schedule,
                note=customer_data.get("note", ""),
                total=total,
                order_type=customer_data.get("order_type", "pickup"),
                payment_method=payment_method,
                order_source="ONLINE_PREORDER",
                status="menunggu",
            )
            db.session.add(new_order)
            db.session.flush()  # Dapatkan order.id

            # Create order items + update sold_count
            for data in order_items_data:
                db.session.add(OrderItem(order_id=new_order.id, **data))
                menu = db.session.get(Menu, data["menu_id"])
                if menu:
                    menu.sold_count = (menu.sold_count or 0) + data["quantity"]

            db.session.commit()

            # Kosongkan cart setelah berhasil
            CartService.clear_cart(session_id)
            return new_order

        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def create_walkin(items: List[dict], customer_data: dict) -> Optional[Order]:
        """
        Buat order walk-in (admin input manual customer datang langsung).
        items: [{menu_id: int, quantity: int}]
        """
        if not items:
            return None

        payment_method = customer_data.get("payment_method", "TUNAI").upper()
        if payment_method not in VALID_PAYMENTS:
            payment_method = "TUNAI"

        try:
            total = 0
            order_items_data = []
            for it in items:
                menu = db.session.get(Menu, it["menu_id"])
                if not menu:
                    continue
                qty = int(it["quantity"])
                subtotal = menu.price * qty
                total += subtotal
                order_items_data.append({
                    "menu_id": menu.id,
                    "quantity": qty,
                    "price_at_order": menu.price,
                    "subtotal": subtotal,
                })

            if total == 0:
                return None

            new_order = Order(
                order_code=OrderService.generate_code(),
                customer_name=customer_data.get("name", "Walk-in"),
                customer_contact=customer_data.get("contact"),
                note=customer_data.get("note", ""),
                total=total,
                order_type="dine-in",
                payment_method=payment_method,
                order_source="WALKIN",
                status="memasak",  # Walk-in langsung diproses
            )
            db.session.add(new_order)
            db.session.flush()

            for data in order_items_data:
                db.session.add(OrderItem(order_id=new_order.id, **data))
                menu = db.session.get(Menu, data["menu_id"])
                if menu:
                    menu.sold_count = (menu.sold_count or 0) + data["quantity"]

            db.session.commit()
            return new_order

        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def get_by_code(order_code: str) -> Optional[Order]:
        """Ambil order + items + menu dalam SATU query (eager loading).

        Lookup case-insensitive karena kode pesanan kadang ditulis ulang
        dengan huruf besar/kecil berbeda (misal oleh chatbot atau saat
        diketik manual oleh pelanggan di /track).
        """
        code = (order_code or "").strip().upper()
        return (
            Order.query.options(joinedload(Order.items).joinedload(OrderItem.menu))
            .filter(func.upper(Order.order_code) == code)
            .first()
        )

    @staticmethod
    def get_recent(limit: int = 20) -> List[Order]:
        """Ambil order terbaru dengan items pre-loaded."""
        return (
            Order.query.options(joinedload(Order.items).joinedload(OrderItem.menu))
            .order_by(Order.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_active() -> List[Order]:
        """Order yang masih diproses (menunggu/memasak/siap)."""
        return (
            Order.query.options(joinedload(Order.items).joinedload(OrderItem.menu))
            .filter(Order.status.in_(["menunggu", "memasak", "siap"]))
            .order_by(Order.created_at.asc())
            .all()
        )

    @staticmethod
    def update_status(order_id: int, new_status: str) -> Optional[Order]:
        if new_status not in VALID_STATUSES:
            raise ValueError(f"Status tidak valid: {new_status}")
        order = db.session.get(Order, order_id)
        if not order:
            return None
        order.status = new_status
        db.session.commit()
        return order

    @staticmethod
    def cancel(order_id: int) -> bool:
        return OrderService.update_status(order_id, "dibatalkan") is not None

    @staticmethod
    def count_active() -> int:
        return Order.query.filter(
            Order.status.in_(["menunggu", "memasak", "siap"])
        ).count()

    @staticmethod
    def count_completed_today() -> int:
        """Order yang selesai hari ini."""
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return Order.query.filter(
            Order.status == "selesai", Order.created_at >= today_start
        ).count()

    @staticmethod
    def count_completed_all() -> int:
        """Semua order yang selesai sepanjang waktu."""
        return Order.query.filter(Order.status == "selesai").count()

    @staticmethod
    def save_rating(order_code: str, rating_val: int) -> bool:
        """Update rata-rata rating menu yang dibeli."""
        if rating_val < 1 or rating_val > 5:
            return False
            
        order = OrderService.get_by_code(order_code)
        if not order:
            return False
            
        # Update rating tiap menu di order ini
        for item in order.items:
            if item.menu:
                if item.menu.rating == 0.0:
                    item.menu.rating = float(rating_val)
                else:
                    item.menu.rating = round((item.menu.rating + rating_val) / 2.0, 1)
                    
        db.session.commit()
        return True
