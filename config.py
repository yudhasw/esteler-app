import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-change-this')

    # Render kasih DATABASE_URL format postgres://, SQLAlchemy butuh postgresql://
    db_url = os.getenv('DATABASE_URL', 'sqlite:///local.db')
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = db_url

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    WHATSAPP_NUMBER = os.getenv('WHATSAPP_NUMBER', '6282287641872')