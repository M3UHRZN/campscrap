import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from contextlib import contextmanager
from loguru import logger
from models.campground import Base  # Base'i models'dan import et

# Veritabanı bağlantı bilgileri
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "campgrounds")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# SQLAlchemy bağlantı URL'si
SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Engine oluştur
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# SessionLocal sınıfı
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Veritabanı tablolarını oluştur"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Veritabanı tabloları başarıyla oluşturuldu.")
    except Exception as e:
        logger.error(f"Veritabanı tabloları oluşturulurken hata: {str(e)}")
        raise

def get_db() -> Generator[Session, None, None]:
    """Veritabanı oturumu döndür (FastAPI Depends için generator olarak)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context():
    """Veritabanı oturumu döndür (with ifadesi için contextmanager olarak)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session():
    """Veritabanı oturumu döndür (doğrudan kullanım için)"""
    return SessionLocal() 