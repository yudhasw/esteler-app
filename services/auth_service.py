from models import db, User
from werkzeug.security import generate_password_hash, check_password_hash


class AuthService:
    @staticmethod
    def register(username, email, password, role="kasir"):
        """Mendaftarkan pengguna/mitra baru."""
        # Cek apakah username/email sudah dipakai
        if (
            User.query.filter_by(username=username).first()
            or User.query.filter_by(email=email).first()
        ):
            return None  # Atau bisa raise Exception khusus

        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username, email=email, password_hash=hashed_password, role=role
        )

        db.session.add(new_user)
        db.session.commit()
        return new_user

    @staticmethod
    def login(username, password):
        """Memverifikasi login pengguna."""
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            return user
        return None
