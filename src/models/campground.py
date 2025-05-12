from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List

Base = declarative_base()

class Campground(Base):
    __tablename__ = 'campgrounds'

    id = Column(Integer, primary_key=True)
    
    # Temel Bilgiler
    name = Column(String(500), nullable=False)
    region_name = Column(String(200))  # Eyalet adı
    administrative_area = Column(String(500))  # Park adı
    nearest_city_name = Column(String(200))
    operator = Column(String(500))  # İşletmeci
    
    # Konum Bilgileri
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location_id = Column(Integer)
    location_type = Column(String(100))
    url = Column(Text, unique=True, nullable=False)
    
    # Özellikler
    accommodation_type_names = Column(JSON)  # ["RVs", "Tents", "Group Sites"]
    camper_types = Column(JSON)  # ["backpacker", "tent", "rv"]
    pin_type = Column(String(100))  # established, dispersed vb.
    
    # Fiyatlandırma
    price_low = Column(String(50))
    price_low_cents = Column(Integer)
    price_low_currency = Column(String(10))
    price_high = Column(String(50))
    price_high_cents = Column(Integer)
    price_high_currency = Column(String(10))
    
    # İstatistikler
    rating = Column(Float)
    reviews_count = Column(Integer)
    photos_count = Column(Integer)
    videos_count = Column(Integer)
    
    # Özellikler (Boolean)
    bookable = Column(Boolean)
    claimed = Column(Boolean)
    booking_method = Column(String(100))  # ridb, external_select vb.
    
    # Medya
    photo_url = Column(Text)
    photo_urls = Column(JSON)  # Fotoğraf URL'leri listesi
    
    # Diğer
    slug = Column(String(500))
    availability_updated_at = Column(DateTime)
    
    # Zaman Bilgileri
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

# Pydantic modelleri
class CampgroundBase(BaseModel):
    name: str
    region_name: Optional[str] = None
    administrative_area: Optional[str] = None
    nearest_city_name: Optional[str] = None
    operator: Optional[str] = None
    latitude: float
    longitude: float
    location_id: Optional[int] = None
    location_type: Optional[str] = None
    url: str
    accommodation_type_names: Optional[List[str]] = None
    camper_types: Optional[List[str]] = None
    pin_type: Optional[str] = None
    price_low: Optional[str] = None
    price_low_cents: Optional[int] = None
    price_low_currency: Optional[str] = None
    price_high: Optional[str] = None
    price_high_cents: Optional[int] = None
    price_high_currency: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    photos_count: Optional[int] = None
    videos_count: Optional[int] = None
    bookable: Optional[bool] = None
    claimed: Optional[bool] = None
    booking_method: Optional[str] = None
    photo_url: Optional[str] = None
    photo_urls: Optional[List[str]] = None
    slug: Optional[str] = None
    availability_updated_at: Optional[datetime] = None

class CampgroundCreate(CampgroundBase):
    pass

class CampgroundUpdate(CampgroundBase):
    pass

class CampgroundInDB(CampgroundBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
