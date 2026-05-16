"""
CartService - keranjang belanja session-based

PERUBAHAN dari versi lama:
- FIX: get_summary() yang keputus di tengah sekarang lengkap
- FIX: N+1 query - eager load Menu pakai joinedload (1 query untuk semua items)
- get_cart auto-create kalau belum ada (idempotent)
- Validasi quantity > 0
"""
from typing import Optional
from sqlalchemy.orm import joinedload
from models import db, Cart, CartItem, Menu


class CartService:
    @staticmethod
    def get_cart(session_id: str) -> Cart:
        """Ambil atau buat keranjang baru (idempotent)."""
        cart = Cart.query.filter_by(session_id=session_id).first()
        if not cart:
            cart = Cart(session_id=session_id)
            db.session.add(cart)
            db.session.commit()
        return cart

    @staticmethod
    def get_cart_with_items(session_id: str) -> Optional[Cart]:
        """
        Ambil cart + items + menu dalam SATU query (eager loading).
        Optimasi penting: hindari N+1 query di halaman cart.
        """
        return (
            Cart.query.options(joinedload(Cart.items).joinedload(CartItem.menu))
            .filter_by(session_id=session_id)
            .first()
        )

    @staticmethod
    def add_item(session_id: str, menu_id: int, quantity: int = 1) -> CartItem:
        """Tambah item ke cart. Kalau sudah ada, increment quantity."""
        if quantity < 1:
            raise ValueError("Quantity harus minimal 1")

        # Validasi menu exists dan aktif
        menu = db.session.get(Menu, menu_id)
        if not menu or not menu.is_active:
            raise ValueError("Menu tidak tersedia")

        cart = CartService.get_cart(session_id)
        item = CartItem.query.filter_by(cart_id=cart.id, menu_id=menu_id).first()

        if item:
            item.quantity += quantity
        else:
            item = CartItem(cart_id=cart.id, menu_id=menu_id, quantity=quantity)
            db.session.add(item)

        db.session.commit()
        return item

    @staticmethod
    def update_quantity(item_id: int, qty: int) -> Optional[CartItem]:
        """Update quantity. Kalau qty <= 0, hapus item."""
        item = db.session.get(CartItem, item_id)
        if not item:
            return None
        if qty <= 0:
            CartService.remove_item(item_id)
            return None
        item.quantity = qty
        db.session.commit()
        return item

    @staticmethod
    def remove_item(item_id: int) -> bool:
        item = db.session.get(CartItem, item_id)
        if not item:
            return False
        db.session.delete(item)
        db.session.commit()
        return True

    @staticmethod
    def clear_cart(session_id: str) -> None:
        """Kosongkan cart (setelah checkout)."""
        cart = Cart.query.filter_by(session_id=session_id).first()
        if cart:
            CartItem.query.filter_by(cart_id=cart.id).delete()
            db.session.commit()

    @staticmethod
    def get_summary(session_id: str) -> dict:
        """
        Hitung total harga & jumlah item di cart.
        FIX: function ini di code lama KEPUTUS di tengah - sekarang lengkap.
        Optimasi: SATU query untuk ambil cart + items + menus (eager loading).
        """
        cart = CartService.get_cart_with_items(session_id)

        if not cart or not cart.items:
            return {
                "items": [],
                "total_price": 0,
                "total_items": 0,
                "is_empty": True,
            }

        items_data = []
        total_price = 0
        total_items = 0

        for item in cart.items:
            if not item.menu or not item.menu.is_active:
                continue  # Skip menu yang sudah tidak aktif
            subtotal = item.menu.price * item.quantity
            items_data.append({
                "id": item.id,
                "menu_id": item.menu.id,
                "name": item.menu.name,
                "image_url": item.menu.image_url,
                "price": item.menu.price,
                "quantity": item.quantity,
                "subtotal": subtotal,
            })
            total_price += subtotal
            total_items += item.quantity

        return {
            "items": items_data,
            "total_price": total_price,
            "total_items": total_items,
            "is_empty": len(items_data) == 0,
        }
