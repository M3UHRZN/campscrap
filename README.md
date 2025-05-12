# Web-Scrape Case Study

## Overview
Develop a scraper to extract all campground locations across the United States from The Dyrt https://thedyrt.com/search by leveraging their map interface which exposes latitude/longitude data through API requests when the mouse moves. You're free to use any library you want (requests, httpx, selenium, playwright)
For questions please connect us via email at info@smart-maple.com

**Hint:** Look for a search endpoint in the network tab!

## Core Requirements
- We provided a Docker compose file, you need to connect to PostgreSQL, create the necessary fields/tables (15p)
- Scrape all campground data from the US map interface and store it in the database (30p)
- Validate the data with pydantic, you can check the necessary fields from src/models/campground.py (these fields are the required fields to store in the db) (15p)
- Scheduling: Cron-like scheduling for regular updates (15p)
- Update: update existing records if they exist. (10p)
- Error handling: handle errors in your code, especially HTTP errors, aand add retries if necessary (15p)

## Bonus
- Database: Use an ORM for PostgreSQL operations
- Logging: Comprehensive logging system
- API Endpoint: Flask/FastAPI endpoint to trigger/control scraper 
  (Hint: you can implement this in an async fashion)
- Performance: Multithreading/async implementation
- Find address from lat/long field
- Feel free to use your creativity every additional field is appreciated

## Scraper Optimizasyonu ve Grid Sistemi
Bu projede ABD'deki tüm kamp alanlarını çekmek için grid sistemi yaklaşımı kullanılmıştır. Grid sistemi şu şekilde çalışır:

- Amerika Birleşik Devletleri'nin tüm coğrafi alanı 20x25 (500) grid hücresine bölünmüştür
- Her bir grid hücresi için API istekleri yapılır ve o bölgedeki kamp alanları çekilir
- Her grid hücresi için sayfalar tek tek işlenir ve her sayfada 500 kamp alanı çekilir
- Grid durumu kaydedilir, böylece işlem kesintiye uğrarsa kaldığı yerden devam edebilir
- Rate limiting ve API sınırlamalarına takılmamak için her istek arasında beklemeler vardır

## Kullanım

Sistemi çalıştırmak için:

```bash
# İlk açılış için 
docker-compose up -d --build

# Docker konteynerları başlat
docker-compose up -d

# API endpoint üzerinden scraper'ı çalıştırma
curl -X POST http://localhost:8000/scrape/

# İstatistikleri görüntüleme
curl http://localhost:8000/stats/
```

Scraper çalışırken ilerlemesini terminal çıktısından takip edebilirsiniz:

```
docker-compose logs -f
```

## Veritabanını Sıfırlama

Veritabanını tamamen sıfırlamak için:

```bash
docker-compose down -v
docker-compose up -d
```
