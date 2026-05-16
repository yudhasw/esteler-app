"""
MenuService - operasi CRUD menu

PERUBAHAN dari versi lama:
- Tambah method search() dan create/update/delete
- get_best_sellers: pakai sold_count ranking (bukan flag manual saja)
- Query dioptimasi (limit, ordering yang konsisten)
"""
from typing import List, Optional
from models import db, Menu


class MenuService:
    @staticmethod
    def get_all(active_only: bool = True) -> List[Menu]:
        """Ambil semua menu, default cuma yang aktif (untuk customer)."""
        query = Menu.query
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(Menu.is_best_seller.desc(), Menu.name.asc()).all()

    @staticmethod
    def get_by_id(menu_id: int) -> Optional[Menu]:
        return db.session.get(Menu, menu_id)  # SQLAlchemy 2.0 style

    @staticmethod
    def get_by_category(category: str, active_only: bool = True) -> List[Menu]:
        query = Menu.query.filter_by(category=category)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.all()

    @staticmethod
    def search(keyword: str, active_only: bool = True) -> List[Menu]:
        """Cari menu berdasarkan kata kunci (nama atau deskripsi)."""
        pattern = f"%{keyword}%"
        query = Menu.query.filter(
            db.or_(Menu.name.ilike(pattern), Menu.description.ilike(pattern))
        )
        if active_only:
            query = query.filter_by(is_active=True)
        return query.all()

    @staticmethod
    def get_best_sellers(limit: int = 5) -> List[Menu]:
        """
        Menu terlaris: gabungan flag is_best_seller + sorted by sold_count.
        """
        return (
            Menu.query.filter_by(is_active=True)
            .order_by(Menu.is_best_seller.desc(), Menu.sold_count.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def create(data: dict) -> Menu:
        menu = Menu(
            name=data["name"],
            description=data.get("description", ""),
            price=int(data["price"]),
            image_url=data.get("image_url"),
            category=data.get("category", "Original"),
            is_active=data.get("is_active", True),
            is_best_seller=data.get("is_best_seller", False),
            is_favorite=data.get("is_favorite", False),
        )
        db.session.add(menu)
        db.session.commit()
        return menu

    @staticmethod
    def update(menu_id: int, data: dict) -> Optional[Menu]:
        menu = db.session.get(Menu, menu_id)
        if not menu:
            return None

        updatable = [
            "name", "description", "price", "image_url",
            "category", "rating", "is_active", "is_best_seller", "is_favorite",
        ]
        for field in updatable:
            if field in data:
                setattr(menu, field, data[field])

        db.session.commit()
        return menu

    @staticmethod
    def delete(menu_id: int) -> bool:
        """Soft delete: set is_active=False (sesuai SDD)."""
        menu = db.session.get(Menu, menu_id)
        if not menu:
            return False
        menu.is_active = False
        db.session.commit()
        return True

    @staticmethod
    def toggle_active(menu_id: int) -> bool:
        menu = db.session.get(Menu, menu_id)
        if not menu:
            return False
        menu.is_active = not menu.is_active
        db.session.commit()
        return True

    @staticmethod
    def count_active() -> int:
        return Menu.query.filter_by(is_active=True).count()
