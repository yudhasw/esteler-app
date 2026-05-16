"""
AuthService - autentikasi admin

PERUBAHAN dari versi lama:
- Pakai User.set_password() dan User.check_password() (DRY)
- Default role 'admin' (TIDAK lagi 'kasir' - karena tabel users khusus admin)
- Eksplisit return type
"""
from typing import Optional
from models import db, User


class AuthService:
    @staticmethod
    def register(
        username: str, email: str, password: str, role: str = "admin"
    ) -> Optional[User]:
        """
        Daftarkan admin baru.
        Return None jika username/email sudah dipakai.
        """
        # Cek duplikat dalam 1 query (lebih efisien daripada 2 query OR)
        existing = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing:
            return None

        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()
        return new_user

    @staticmethod
    def login(username: str, password: str) -> Optional[User]:
        """Verifikasi login. Return User object kalau valid, None kalau gagal."""
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            return user
        return None

    @staticmethod
    def get_by_email(email: str) -> Optional[User]:
        return User.query.filter_by(email=email).first()
