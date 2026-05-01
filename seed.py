"""Buat akun penjual awal. Jalankan: python seed.py"""
from app import app
from models import db, Seller

with app.app_context():
    if Seller.query.filter_by(username='warungbudi').first():
        print("Akun sudah ada")
    else:
        seller = Seller(
            username='warungbudi',
            shop_name='Warung Pak Budi',
            whatsapp='6281234567890'
        )
        seller.set_password('rahasia123')
        db.session.add(seller)
        db.session.commit()
        print("✅ Akun dibuat: warungbudi / rahasia123")