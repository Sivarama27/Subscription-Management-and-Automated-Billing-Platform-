from celery import Celery
from celery.schedules import crontab
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")

celery_app = Celery(
    "billing_platform",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "generate-due-billing-cycles-daily": {
        "task": "app.tasks.generate_due_billing_cycles",
        "schedule": crontab(hour=0, minute=0),
    },
    "generate-invoices-from-pending-cycles": {
        "task": "app.tasks.generate_invoices_from_pending_cycles",
        "schedule": crontab(hour=1, minute=0),
    },
    "process-due-payment-retries": {
        "task": "app.tasks.process_due_payment_retries",
        "schedule": crontab(minute="*/30"),   # every 30 minutes, since retries need to fire close to their scheduled time, not just once a day
    },
}

import app.tasks