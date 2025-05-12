import time
import re
import requests
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.campground import Campground, CampgroundCreate
from database import get_db_context
import concurrent.futures
from itertools import islice
import os
import json
import random

class DyrtScraper:
    def __init__(self):
        self.base_url = "https://thedyrt.com/api/v6/locations/search-results"  # Doğru API endpoint'i
        self.fields = [
            "name", "region-name", "administrative-area", "nearest-city-name",
            "operator", "latitude", "longitude", "location-id", "location-type",
            "accommodation-type-names", "camper-types", "pin-type",
            "price-low", "price-low-cents", "price-low-currency",
            "price-high", "price-high-cents", "price-high-currency",
            "rating", "reviews-count", "photos-count", "videos-count",
            "bookable", "claimed", "booking-method",
            "photo-url", "photo-urls", "slug", "availability-updated-at",
            "created-at", "updated-at"
        ]
        # Grid sistemi için ABD sınırları
        self.min_lng, self.min_lat = -125.0, 24.3963  # Batı ve Güney
        self.max_lng, self.max_lat = -66.9346, 49.3844  # Doğu ve Kuzey
        self.grid_x = 20  # Yatayda 20 parça
        self.grid_y = 25    # Dikeyde 25 parça
        
        # Rate limiting ve paralellik için ayarlar
        self.max_workers = 3  # Paralel istek sayısı (API sınırlaması için azaltıldı)
        self.max_retries = 5  # Maksimum yeniden deneme sayısı
        self.page_size = 500  # Sayfa başına veri sayısı (maksimum değere yükseltildi)
        self.pages_per_batch = 1  # Her batch'te çekilecek sayfa sayısı
        self.batch_delay = 1     # Batch'ler arası bekleme süresi (saniye)
        
        # Durum takibi için ayarlar
        self.state_cache_file = "grid_state_cache.json"
        self.current_grid_x = 0
        self.current_grid_y = 0
        self.current_page = 1
        self.load_state()

    def slugify(self, text: str) -> str:
        """Metni URL-dostu formata dönüştür"""
        if not text:
            return ""
        return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

    def load_state(self):
        """Çalışma durumunu yükle, böylece kesinti durumunda kaldığı yerden devam edebilir"""
        if os.path.exists(self.state_cache_file):
            try:
                with open(self.state_cache_file, 'r') as f:
                    state = json.load(f)
                    self.current_grid_x = state.get('grid_x', 0)
                    self.current_grid_y = state.get('grid_y', 0)
                    self.current_page = state.get('page', 1)
                    logger.info(f"Kayıtlı durum yüklendi: Grid ({self.current_grid_x},{self.current_grid_y}), Sayfa {self.current_page}")
            except Exception as e:
                logger.error(f"Durum yüklenirken hata: {str(e)}")
                self.current_grid_x = 0
                self.current_grid_y = 0
                self.current_page = 1
        else:
            self.current_grid_x = 0
            self.current_grid_y = 0
            self.current_page = 1

    def save_state(self):
        """Çalışma durumunu kaydet"""
        try:
            state = {
                'grid_x': self.current_grid_x,
                'grid_y': self.current_grid_y,
                'page': self.current_page
            }
            with open(self.state_cache_file, 'w') as f:
                json.dump(state, f)
            logger.info(f"Durum kaydedildi: Grid ({self.current_grid_x},{self.current_grid_y}), Sayfa {self.current_page}")
        except Exception as e:
            logger.error(f"Durum kaydedilirken hata: {str(e)}")

    def get_bbox_for_grid(self, grid_x: int, grid_y: int) -> str:
        """Belirli bir grid konumu için bbox hesapla"""
        lng_step = (self.max_lng - self.min_lng) / self.grid_x
        lat_step = (self.max_lat - self.min_lat) / self.grid_y
        
        bbox = [
            self.min_lng + grid_x * lng_step,  # min_lng
            self.min_lat + grid_y * lat_step,  # min_lat
            self.min_lng + (grid_x + 1) * lng_step,  # max_lng
            self.min_lat + (grid_y + 1) * lat_step   # max_lat
        ]
        return f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"

    def fetch_page(self, grid_x: int, grid_y: int, page: int) -> List[Dict[str, Any]]:
        """Belirli bir grid konumu için tek bir sayfayı çek"""
        bbox_str = self.get_bbox_for_grid(grid_x, grid_y)
        
        for retry in range(self.max_retries):
            try:
                # Farklı sort parametreleri deneyerek API'yi optimize edelim
                sort_options = ["recommended", "name-raw", "-rating,-reviews-count", "-reviews-count", 
                                "price-low-cents,price-high-cents", "-price-high-cents,-price-low-cents"]
                
                params = {
                    "filter[search][bbox]": bbox_str,
                    "page[number]": page,
                    "page[size]": self.page_size,
                    "sort": random.choice(sort_options)
                }
                
                # User-Agent'ı değiştirerek daha insana benzer davranış gösterelim
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://thedyrt.com/search"
                }
                
                # API'ye istek gönder
                logger.info(f"Grid ({grid_x},{grid_y}) - Sayfa {page} isteniyor... (Deneme {retry + 1}/{self.max_retries})")
                response = requests.get(self.base_url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if not data.get("data"):
                    logger.warning(f"Grid ({grid_x},{grid_y}) - Sayfa {page} için veri bulunamadı.")
                    return []
                
                page_campgrounds = []
                for item in data["data"]:
                    attr = item["attributes"]
                    row = {}
                    for field in self.fields:
                        val = attr.get(field)
                        row[field] = val
                    
                    # URL oluştur
                    state_slug = self.slugify(attr.get("region-name", ""))
                    slug = attr.get("slug") or ""
                    row["url"] = f"https://thedyrt.com/camping/{state_slug}/{slug}"
                    
                    page_campgrounds.append(row)
                
                logger.info(f"Grid ({grid_x},{grid_y}) - Sayfa {page}: {len(page_campgrounds)} kamp alanı bulundu.")
                
                # API rate limiting'e takılmamak için rastgele bir süre bekle
                jitter = random.uniform(0.5, 1.5)
                time.sleep(1 * jitter)
                
                return page_campgrounds
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Grid ({grid_x},{grid_y}) - Sayfa {page} çekilirken hata (Deneme {retry + 1}/{self.max_retries}): {str(e)}")
                if retry < self.max_retries - 1:
                    # Exponential backoff ile bekleme süresi
                    wait_time = (2 ** retry) + random.random() * 2
                    logger.info(f"Yeniden denemeden önce {wait_time:.2f} saniye bekleniyor...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Grid ({grid_x},{grid_y}) - Sayfa {page} için maksimum deneme sayısına ulaşıldı.")
                    return []

    def get_campgrounds(self) -> List[Dict[str, Any]]:
        """Tüm ABD'deki kamp alanlarını grid sistemi kullanarak çek"""
        all_campgrounds = []
        total_regions = self.grid_x * self.grid_y
        
        # Eğer daha önce çalışma durumu kaydedilmişse, oradan devam et
        logger.info(f"Başlangıç konumu: Grid ({self.current_grid_x},{self.current_grid_y}), Sayfa {self.current_page}")
        
        for i in range(self.current_grid_x, self.grid_x):
            for j in range(self.current_grid_y, self.grid_y):
                # Yalnızca şu anki satırın ilk hücresinde kalan sayfalardan başla
                # Diğer satırlar için sayfa 1'den başla
                start_page = self.current_page if i == self.current_grid_x and j == self.current_grid_y else 1
                
                current_region = i * self.grid_y + j + 1
                logger.info(f"Grid ({i},{j}) bölgesi çekiliyor ({current_region}/{total_regions})")
                
                page = start_page
                region_campgrounds = 0
                
                # Her grid hücresi için sayfaları tek tek işle
                while True:
                    # Durumu kaydet
                    self.current_grid_x = i
                    self.current_grid_y = j
                    self.current_page = page
                    self.save_state()
                    
                    # Sayfayı çek
                    page_campgrounds = self.fetch_page(i, j, page)
                    if not page_campgrounds:
                        break
                    
                    all_campgrounds.extend(page_campgrounds)
                    region_campgrounds += len(page_campgrounds)
                    
                    # Rate limiting'e takılmamak için sayfalar arasında bekleme
                    jitter = random.uniform(0.8, 1.2)
                    wait_time = 1 * jitter  # 2 saniye civarı bekle
                    logger.info(f"Rate limiting için {wait_time:.2f} saniye bekleniyor...")
                    time.sleep(wait_time)
                    
                    # Sonraki sayfa var mı kontrol et (API'den dönen meta bilgisine bakarak)
                    if not page_campgrounds or len(page_campgrounds) < self.page_size:
                        logger.info(f"Grid ({i},{j}) tamamlandı. Toplam: {region_campgrounds} kamp alanı")
                        break
                    
                    page += 1
                
                # Her grid hücresi işlendikten sonra daha uzun süre bekleyelim
                logger.info(f"Grid ({i},{j}) bölgesi tamamlandı. {region_campgrounds} kamp alanı bulundu.")
                if not (i == self.grid_x - 1 and j == self.grid_y - 1):  # Son grid hücresi değilse bekle
                    jitter = random.uniform(0.8, 1.2)
                    wait_time = self.batch_delay * jitter
                    logger.info(f"Yeni grid bölgesine geçmeden önce {wait_time:.2f} saniye bekleniyor...")
                    time.sleep(wait_time)
                
                # Sonraki grid için sayfa numarasını sıfırla
                self.current_page = 1
            
            # Satır değiştiğinde y koordinatını sıfırla
            self.current_grid_y = 0

        # Çalışma tamamlandığında state'i sıfırla
        self.current_grid_x = 0
        self.current_grid_y = 0
        self.current_page = 1
        self.save_state()

        # Tekrar eden kamp alanlarını kaldır
        unique = {(c['name'], c['latitude'], c['longitude']): c for c in all_campgrounds 
                if c.get('name') and c.get('latitude') and c.get('longitude')}
        unique_campgrounds = list(unique.values())
        logger.info(f"Toplam {len(all_campgrounds)} kamp alanı bulundu, {len(unique_campgrounds)} benzersiz kamp alanı kaydedilecek.")
        return unique_campgrounds

    def save_to_database(self, campgrounds: List[Dict[str, Any]]) -> None:
        """Kamp alanlarını veritabanına kaydet"""
        logger.info("Veritabanına kaydediliyor...")
        
        with get_db_context() as db:
            try:
                total = len(campgrounds)
                for i, row in enumerate(campgrounds, 1):
                    if i % 100 == 0 or i == total:
                        logger.info(f"İlerleme: {i}/{total} ({i/total*100:.1f}%)")
                    
                    # Dönüşümler
                    if row.get('availability-updated-at'):
                        try:
                            row['availability_updated_at'] = datetime.fromisoformat(
                                row['availability-updated-at'].replace('Z', '+00:00')
                            )
                        except:
                            row['availability_updated_at'] = None
                    else:
                        row['availability_updated_at'] = None

                    # Tarih alanlarını dönüştür
                    for field in ['created-at', 'updated-at']:
                        if row.get(field):
                            try:
                                row[field.replace('-', '_')] = datetime.fromisoformat(
                                    row[field].replace('Z', '+00:00')
                                )
                            except:
                                row[field.replace('-', '_')] = None
                        else:
                            row[field.replace('-', '_')] = None

                    # Boolean alanları dönüştür
                    for field in ['bookable', 'claimed']:
                        if field in row:
                            val = row[field]
                            if isinstance(val, str):
                                row[field] = val.lower() == 'true'
                            else:
                                row[field] = bool(val)

                    # Sayısal alanları dönüştür
                    for field in ['photos-count', 'price-low-cents', 'price-high-cents', 'reviews-count', 'videos-count']:
                        if field in row and row[field]:
                            try:
                                row[field.replace('-', '_')] = int(row[field])
                            except:
                                row[field.replace('-', '_')] = None

                    # Float alanları dönüştür
                    for field in ['rating']:
                        if field in row and row[field]:
                            try:
                                row[field] = float(row[field])
                            except:
                                row[field] = None

                    # Campground modeli için veri hazırla
                    campground_data = {
                        "name": row.get("name"),
                        "region_name": row.get("region-name"),
                        "administrative_area": row.get("administrative-area"),
                        "nearest_city_name": row.get("nearest-city-name"),
                        "operator": row.get("operator"),
                        "latitude": row.get("latitude"),
                        "longitude": row.get("longitude"),
                        "location_id": row.get("location-id"),
                        "location_type": row.get("location-type"),
                        "accommodation_type_names": row.get("accommodation-type-names"),
                        "camper_types": row.get("camper-types"),
                        "pin_type": row.get("pin-type"),
                        "price_low": row.get("price-low"),
                        "price_low_cents": row.get("price-low-cents"),
                        "price_low_currency": row.get("price-low-currency"),
                        "price_high": row.get("price-high"),
                        "price_high_cents": row.get("price-high-cents"),
                        "price_high_currency": row.get("price-high-currency"),
                        "rating": row.get("rating"),
                        "reviews_count": row.get("reviews-count"),
                        "photos_count": row.get("photos-count"),
                        "videos_count": row.get("videos-count"),
                        "bookable": row.get("bookable"),
                        "claimed": row.get("claimed"),
                        "booking_method": row.get("booking-method"),
                        "photo_url": row.get("photo-url"),
                        "photo_urls": row.get("photo-urls"),
                        "slug": row.get("slug"),
                        "availability_updated_at": row.get("availability_updated_at"),
                        "created_at": row.get("created_at"),
                        "updated_at": row.get("updated_at"),
                        "url": row.get("url")
                    }
                    
                    # URL'ye göre var olan kaydı kontrol et (update için)
                    if campground_data.get("url"):
                        existing = db.query(Campground).filter(Campground.url == campground_data["url"]).first()
                        if existing:
                            # Kaydı güncelle
                            for key, value in campground_data.items():
                                if value is not None and hasattr(existing, key):
                                    setattr(existing, key, value)
                            logger.debug(f"Kampground güncellendi: {campground_data['name']}")
                        else:
                            # Yeni kayıt ekle
                            campground = Campground(**campground_data)
                            db.add(campground)
                            logger.debug(f"Yeni kampground eklendi: {campground_data['name']}")
                
                db.commit()
                logger.info(f"Toplam {total} kamp alanı başarıyla veritabanına kaydedildi.")
            except Exception as e:
                logger.error(f"Veritabanına kaydetme sırasında hata: {str(e)}")
                db.rollback()

def run_scraper():
    """Scraper'ı çalıştır"""
    try:
        logger.info("The Dyrt Scraper başlatılıyor...")
        scraper = DyrtScraper()
        campgrounds = scraper.get_campgrounds()
        logger.info(f"Toplam {len(campgrounds)} benzersiz kamp alanı bulundu.")
        scraper.save_to_database(campgrounds)
        logger.info("Scraper başarıyla tamamlandı.")
    except Exception as e:
        logger.error(f"Scraper hatası: {str(e)}")
        raise

if __name__ == "__main__":
    run_scraper() 