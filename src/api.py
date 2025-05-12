from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from loguru import logger

from database import get_db, init_db
from models.campground import Campground, CampgroundCreate, CampgroundInDB
from scraper import run_scraper
from scheduler import setup_scheduler

app = FastAPI(title="Kamp Alanı API")

# Zamanlanmış görevler için global değişken
scheduler = None

@app.on_event("startup")
async def startup_event():
    """Uygulama başlatıldığında çalışır"""
    # Veritabanını hazırla
    init_db()
    
    # Zamanlanmış görevleri başlat
    global scheduler
    scheduler = setup_scheduler()
    logger.info("Uygulama ve zamanlanmış görevler başlatıldı.")

@app.on_event("shutdown")
async def shutdown_event():
    """Uygulama kapatıldığında çalışır"""
    # Zamanlanmış görevleri durdur
    global scheduler
    if scheduler:
        scheduler.shutdown()
        logger.info("Zamanlanmış görevler durduruldu.")

@app.get("/")
async def root():
    return {"message": "Kamp Alanı API'sine Hoş Geldiniz"}

@app.get("/campgrounds/", response_model=List[CampgroundInDB])
async def get_campgrounds(
    skip: int = 0,
    limit: int = 100,
    region: str = None,
    db: Session = Depends(get_db)
):
    """Tüm kamp alanlarını listele"""
    query = db.query(Campground)
    if region:
        query = query.filter(Campground.region_name == region)
    return query.offset(skip).limit(limit).all()

@app.get("/campgrounds/{campground_id}", response_model=CampgroundInDB)
async def get_campground(campground_id: int, db: Session = Depends(get_db)):
    """Belirli bir kamp alanının detaylarını getir"""
    campground = db.query(Campground).filter(Campground.id == campground_id).first()
    if campground is None:
        raise HTTPException(status_code=404, detail="Kamp alanı bulunamadı")
    return campground

@app.post("/scrape/")
async def trigger_scrape():
    """Manuel olarak veri çekme işlemini başlat"""
    try:
        run_scraper()
        return {"message": "Veri çekme işlemi başarıyla tamamlandı"}
    except Exception as e:
        logger.error(f"Veri çekme işlemi sırasında hata: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats/")
async def get_stats(db: Session = Depends(get_db)):
    """Kamp alanları hakkında istatistikler"""
    total = db.query(Campground).count()
    regions = db.query(Campground.region_name, func.count(Campground.id))\
        .group_by(Campground.region_name)\
        .all()
    
    return {
        "total_campgrounds": total,
        "regions": {region: count for region, count in regions}
    }

@app.get("/scheduler/status/")
async def get_scheduler_status():
    """Zamanlanmış görevler hakkında bilgi verir"""
    global scheduler
    if not scheduler:
        return {"status": "not_running", "next_run": None}
    
    jobs = scheduler.get_jobs()
    return {
        "status": "running" if scheduler.running else "stopped",
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else "Not scheduled"
            } 
            for job in jobs
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 