"""
Seed data awal untuk Dapur Hijrah.
Jalankan: python seed.py

PERUBAHAN dari versi lama:
- Pakai model BARU (User, Menu) - bukan Seller (sudah dihapus)
- Tambah sample menu yang sesuai design (Es Teler, Salmon Bowl, Pizza, dll)
"""
from api.index import app
from models import db, User, Menu


def seed():
    with app.app_context():
        # === Admin Default ===
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", email="admin@dapurhijrah.id", role="admin")
            admin.set_password("admin123")
            db.session.add(admin)
            print("✅ Admin dibuat: admin / admin123")

        # === Sample Menus ===
        sample_menus = [
            {
                "name": "Es Teler Spesial",
                "description": "Es teler klasik dengan kelapa muda, alpukat, nangka, dan susu kental manis.",
                "price": 25000,
                "category": "Original",
                "image_url": "https://images.unsplash.com/photo-1502741338009-cac2772e18bc?w=400",
                "is_best_seller": True,
                "rating": 4.8,
                "sold_count": 342,
            },
            {
                "name": "Es Teler Durian",
                "description": "Es teler dengan tambahan durian montong asli, manis dan creamy.",
                "price": 35000,
                "category": "Premium",
                "image_url": "https://images.unsplash.com/photo-1567337710282-00832b415979?w=400",
                "is_favorite": True,
                "rating": 4.9,
                "sold_count": 289,
            },
            {
                "name": "Es Teler Salmon Bowl",
                "description": "Variasi modern dengan topping salmon segar dan alpukat.",
                "price": 85000,
                "category": "Signature",
                "image_url": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400",
                "rating": 4.7,
                "sold_count": 156,
            },
            {
                "name": "Hummus Garden",
                "description": "Side dish hummus dengan sayuran segar.",
                "price": 55000,
                "category": "Side",
                "image_url": "https://images.unsplash.com/photo-1571197119282-7c4b8d8a40c1?w=400",
                "is_best_seller": True,
                "rating": 4.8,
                "sold_count": 198,
            },
            {
                "name": "Margherita Neo",
                "description": "Pizza margherita dengan keju mozzarella premium.",
                "price": 95000,
                "category": "Main",
                "image_url": "https://images.unsplash.com/photo-1604068549290-dea0e4a305ca?w=400",
                "is_favorite": True,
                "rating": 4.9,
                "sold_count": 234,
            },
            {
                "name": "Pesto Genovese",
                "description": "Pasta dengan saus pesto basil khas Italia.",
                "price": 75000,
                "category": "Main",
                "image_url": "https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=400",
                "is_best_seller": True,
                "rating": 4.7,
                "sold_count": 167,
            },
            {
                "name": "Dragon Blast",
                "description": "Smoothie bowl dengan dragon fruit dan granola.",
                "price": 45000,
                "category": "Beverages",
                "image_url": "https://images.unsplash.com/photo-1571805529673-0f56b922b359?w=400",
                "rating": 4.6,
                "sold_count": 145,
            },
            {
                "name": "Es Teh Manis",
                "description": "Teh manis dingin segar.",
                "price": 8000,
                "category": "Beverages",
                "image_url": "https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=400",
                "rating": 4.5,
                "sold_count": 421,
            },
        ]

        for data in sample_menus:
            if not Menu.query.filter_by(name=data["name"]).first():
                db.session.add(Menu(**data))
                print(f"✅ Menu ditambahkan: {data['name']}")

        db.session.commit()
        print("\n✨ Seed selesai!")


if __name__ == "__main__":
    seed()
