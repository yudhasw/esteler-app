import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Mengambil URL dari .env, jika tidak ada gunakan default (opsional)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "kode-rahasia-esteler")
