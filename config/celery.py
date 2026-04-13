import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("airline_system")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "process-outbox-messages": {
        "task": "apps.core.tasks.process_outbox_messages",
        "schedule": 10.0,
    },
    "cleanup-expired-idempotency-keys": {
        "task": "apps.core.tasks.cleanup_expired_idempotency_keys",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "health-check-sync": {
        "task": "apps.core.tasks.health_check_sync",
        "schedule": 60.0,
    },
}

app.conf.timezone = "UTC"

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')