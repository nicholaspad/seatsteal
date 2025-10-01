from celery import Celery
from celery.schedules import crontab
from ...config import settings

# Initialize Celery (same configuration as tasks.py)
celery_app = Celery(
    'notifications',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configure periodic tasks using Celery Beat
celery_app.conf.beat_schedule = {
    # Check for notifications every 5 minutes
    'check-notifications-every-5-minutes': {
        'task': 'notifications.check_and_send',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
        'args': (),
    },

    # More frequent checks during peak registration times
    # Every 2 minutes during peak hours (8 AM - 8 PM ET)
    'check-notifications-peak-hours': {
        'task': 'notifications.check_and_send',
        'schedule': crontab(minute='*/2', hour='8-20'),  # Every 2 min, 8am-8pm
        'args': (),
    },

    # Cleanup old notification records weekly
    'cleanup-old-notifications-weekly': {
        'task': 'notifications.cleanup_old',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Sunday 3 AM
        'args': (30,),  # Keep 30 days
    },

    # Health check every 5 minutes
    'notifications-health-check': {
        'task': 'notifications.health_check',
        'schedule': crontab(minute='*/5'),
        'args': (),
    },
}

# Celery Beat configuration
celery_app.conf.update(
    timezone='UTC',
    enable_utc=True,
    beat_schedule_filename='/tmp/celerybeat-notifications-schedule',  # Persist schedule
)
