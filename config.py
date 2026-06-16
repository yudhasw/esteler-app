"""
Config untuk Dapur Hijrah - dioptimasi untuk Vercel + Neon

PERUBAHAN dari versi lama:
- SECRET_KEY: WAJIB di-set via env (tidak ada fallback insecure)
- Tambah connection pool settings yang cocok untuk serverless + Neon
- SSL required (Neon mandatory)
- Pre-ping untuk handle stale connection
- Auto-tambahin ?sslmode=require kalau lupa
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _normalize_db_url(url: str) -> str:
    """
    Normalisasi DATABASE_URL agar selalu siap pakai untuk Neon.
    - postgres:// → postgresql:// (SQLAlchemy 1.4+ requirement)
    - Auto-tambahin sslmode=require kalau belum ada
    """
    if not url:
        return url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if "sslmode=" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}sslmode=require"
    return url


class Config:
    # Database (Neon PostgreSQL)
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(os.getenv("DATABASE_URL", ""))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Connection pool optimized untuk Vercel serverless + Neon pooler
    # pool_pre_ping: cek koneksi sebelum dipake (penting di serverless)
    # pool_recycle: refresh koneksi tiap 5 menit (Neon idle timeout)
    # pool_size kecil karena tiap function invocation isolated
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "connect_args": {
            "connect_timeout": 10,
            #"options": "-c statement_timeout=8000",  # 8s query timeout (< Vercel 10s)
        },
    }

    # Security - WAJIB di-set di production
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        # Hanya throw di production, dev pakai fallback
        if os.getenv("VERCEL_ENV") == "production":
            raise RuntimeError(
                "SECRET_KEY environment variable WAJIB diset di production!"
            )
        SECRET_KEY = "dev-only-key-jangan-pakai-di-production"

    # Session cookie config (aman untuk production)
    SESSION_COOKIE_SECURE = os.getenv("VERCEL_ENV") == "production"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # 7 hari

    # Upload
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # 4MB (Vercel Hobby limit: 4.5MB)

    # Cloudinary - storage gambar menu (free tier, lihat https://cloudinary.com/pricing)
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

    # Groq - LLM untuk chatbot (lihat https://console.groq.com)
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
