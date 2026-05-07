from models import db, Cart, CartItem, Menu


class CartService:
    @staticmethod
    def get_cart(session_id):
        """Mengambil atau membuat keranjang baru berdasarkan session_id."""
        cart = Cart.query.filter_by(session_id=session_id).first()
        if not cart:
            cart = Cart(session_id=session_id)
            db.session.add(cart)
            db.session.commit()
        return cart

    @staticmethod
    def add_item(session_id, menu_id, quantity=1):
        """Menambahkan item ke dalam keranjang."""
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
    def update_quantity(item_id, qty):
        """Mengubah jumlah pesanan dalam keranjang."""
        item = CartItem.query.get(item_id)
        if item:
            if qty <= 0:
                return CartService.remove_item(item_id)
            item.quantity = qty
            db.session.commit()
            return item
        return None

    @staticmethod
    def remove_item(item_id):
        """Menghapus satu item dari keranjang."""
        item = CartItem.query.get(item_id)
        if item:
            db.session.delete(item)
            db.session.commit()
            return True
        return False

    @staticmethod
    def clear_cart(session_id):
        """Mengosongkan seluruh isi keranjang."""
        cart = Cart.query.filter_by(session_id=session_id).first()
        if cart:
            CartItem.query.filter_by(cart_id=cart.id).delete()
            db.session.commit()

    @staticmethod
    def get_summary(session_id):
        """Menghitung total harga dan jumlah item di keranjang."""
        cart = CartService.get_cart(session_id)
        total_price = 0
        total_items = 0

        for item in cart.items:
            menu = Menu.query
