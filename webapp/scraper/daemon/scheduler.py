from celery import Celery
from celery.schedules import crontab
from ...config import settings

# Initialize Celery (same configuration as tasks.py)
celery_app = Celery(
    'scraper',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configure periodic tasks using Celery Beat
celery_app.conf.beat_schedule = {
    # Scrape all colleges every hour
    'scrape-all-colleges-hourly': {
        'task': 'scraper.scrape_all_colleges',
        'schedule': crontab(minute=0),  # Every hour at minute 0
        'args': (),
    },

    # Scrape all colleges more frequently during peak registration times
    # This runs every 15 minutes during peak hours (8 AM - 8 PM ET)
    'scrape-all-colleges-peak-hours': {
        'task': 'scraper.scrape_all_colleges',
        'schedule': crontab(minute='*/15', hour='8-20'),  # Every 15 min, 8am-8pm
        'args': (),
    },

    # Health check every 5 minutes
    'scraper-health-check': {
        'task': 'scraper.health_check',
        'schedule': crontab(minute='*/5'),
        'args': (),
    },
}

# Celery Beat configuration
celery_app.conf.update(
    timezone='UTC',
    enable_utc=True,
    beat_schedule_filename='/tmp/celerybeat-scraper-schedule',  # Persist schedule
)
