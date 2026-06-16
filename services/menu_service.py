"""
MenuService - operasi CRUD menu

PERUBAHAN dari versi lama:
- Tambah method search() dan create/update/delete
- get_best_sellers: pakai sold_count ranking (bukan flag manual saja)
- Query dioptimasi (limit, ordering yang konsisten)
"""
import re
from typing import List, Optional
from models import db, Menu


# Kata-kata yang sering ikut terbawa saat LLM mengirim frasa mentah
# pelanggan sebagai keyword (misal "pesan 2 es teler ori") - dibuang
# supaya pencarian tetap match ke nama menu ("Es Teler Ori Regular").
_SEARCH_STOPWORDS = {
    "pesan", "pesanan", "mau", "ingin", "beli", "tolong", "dong", "ya",
    "saya", "aku", "minta", "order", "buat", "untuk", "satu", "dua",
    "tiga", "empat", "lima", "porsi", "pcs", "buah", "biji", "es",
    "teler",
}


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
        """Cari menu berdasarkan kata kunci (nama atau deskripsi).

        Keyword dibersihkan dulu (hapus angka & kata filler seperti "pesan",
        "mau") dan dipecah per kata, lalu di-AND-kan - supaya frasa mentah
        seperti "pesan 2 es teler ori" tetap match ke "Es Teler Ori Regular".
        Kalau hasil AND kosong, fallback ke pencarian substring keyword asli.
        """
        raw = (keyword or "").strip()
        cleaned = re.sub(r"\d+", " ", raw.lower())
        terms = [w for w in cleaned.split() if w not in _SEARCH_STOPWORDS]
        if not terms:
            terms = [raw] if raw else []

        query = Menu.query
        for term in terms:
            pattern = f"%{term}%"
            query = query.filter(
                db.or_(Menu.name.ilike(pattern), Menu.description.ilike(pattern))
            )
        if active_only:
            query = query.filter_by(is_active=True)
        results = query.all()
        if results or not raw:
            return results

        # Fallback: AND per-term tidak menemukan apapun, coba substring penuh.
        fallback_query = Menu.query.filter(
            db.or_(Menu.name.ilike(f"%{raw}%"), Menu.description.ilike(f"%{raw}%"))
        )
        if active_only:
            fallback_query = fallback_query.filter_by(is_active=True)
        return fallback_query.all()

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
