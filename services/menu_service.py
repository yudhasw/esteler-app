from models import db, Menu


class MenuService:
    @staticmethod
    def get_all(active_only=True):
        """Mengambil semua menu, bisa difilter yang aktif saja."""
        if active_only:
            return Menu.query.filter_by(is_active=True).all()
        return Menu.query.all()

    @staticmethod
    def get_by_id(menu_id):
        """Mencari menu spesifik berdasarkan ID."""
        return Menu.query.get(menu_id)

    @staticmethod
    def get_best_sellers(limit=3):
        """Mengambil daftar menu paling laris."""
        return (
            Menu.query.filter_by(is_active=True, is_best_seller=True).limit(limit).all()
        )

    @staticmethod
    def toggle_active(menu_id):
        """Mengaktifkan/menonaktifkan menu (misal saat bahan baku habis)."""
        menu = Menu.query.get(menu_id)
        if menu:
            menu.is_active = not menu.is_active
            db.session.commit()
            return True
        return False
