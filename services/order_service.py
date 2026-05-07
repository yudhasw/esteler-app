import uuid
from models import db, Order, OrderItem, Menu
from services.cart_service import CartService


class OrderService:
    @staticmethod
    def create_order(session_id, customer_data):
        """Membuat pesanan baru dari isi keranjang."""
        cart = CartService.get_cart(session_id)
        if not cart.items:
            return None

        # Generate order code pendek (misal: ORD-A1B2)
        order_code = f"ORD-{uuid.uuid4().hex[:4].upper()}"
        summary = CartService.get_summary(session_id)

        new_order = Order(
            order_code=order_code,
            customer_name=customer_data.get("name", "Pelanggan"),
            pickup_schedule=customer_data.get("pickup_schedule"),
            note=customer_data.get("note", ""),
            total=summary["total_price"],
            order_type=customer_data.get("order_type", "pickup"),
        )
        db.session.add(new_order)
        db.session.flush()  # Untuk mendapatkan new_order.id

        # Pindahkan item dari Cart ke OrderItem
        for item in cart.items:
            menu = Menu.query.get(item.menu_id)
            if menu:
                order_item = OrderItem(
                    order_id=new_order.id,
                    menu_id=item.menu_id,
                    quantity=item.quantity,
                    price_at_order=menu.price,
                    subtotal=(menu.price * item.quantity),
                )
                db.session.add(order_item)

                # Update sold_count pada Menu
                menu.sold_count += item.quantity

        db.session.commit()
        CartService.clear_cart(session_id)  # Kosongkan keranjang setelah order
        return new_order

    @staticmethod
    def get_by_code(order_code):
        return Order.query.filter_by(order_code=order_code).first()

    @staticmethod
    def get_recent(limit=10):
        return Order.query.order_by(Order.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_active():
        return Order.query.filter(Order.status.in_(["menunggu", "memasak"])).all()

    @staticmethod
    def update_status(order_id, new_status):
        order = Order.query.get(order_id)
        if order:
            order.status = new_status
            db.session.commit()
            return order
        return None

    @staticmethod
    def cancel(order_id):
        return OrderService.update_status(order_id, "dibatalkan") is not None

    @staticmethod
    def generate_receipt(order_id):
        # Stub untuk generate PDF receipt (Bisa pakai library WeasyPrint/ReportLab nanti)
        return b"PDF_RECEIPT_DATA_MOCK"

    @staticmethod
    def track_status(order_code):
        order = OrderService.get_by_code(order_code)
        if order:
            return order.to_dict()
        return None
