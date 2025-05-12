from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from scraper import run_scraper

def setup_scheduler():
    """Zamanlanmış görevleri ayarla ve scheduler'ı döndür"""
    scheduler = BackgroundScheduler()
    
    # Her gün gece yarısı çalışacak şekilde ayarla
    scheduler.add_job(
        run_scraper,
        trigger=CronTrigger(hour=0, minute=0),
        id='daily_scrape',
        name='Günlük kamp alanı güncelleme',
        replace_existing=True
    )
    
    try:
        scheduler.start()
        logger.info("Zamanlanmış görevler başlatıldı.")
        return scheduler
    except Exception as e:
        logger.error(f"Zamanlanmış görevler başlatılırken hata: {str(e)}")
        raise

if __name__ == "__main__":
    # Test için
    scheduler = setup_scheduler()
    
    try:
        # Scheduler çalışırken program kapatılmamalı
        import time
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        # Program sonlandığında scheduler'ı durdur
        scheduler.shutdown() 