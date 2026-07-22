"""
Celery application instance.

Celery is our async task queue — it runs background jobs (like sending emails)
without blocking the HTTP response. Redis is the message broker that queues
the tasks.

Architecture:
  HTTP request -> service.py -> notify.py -> celery task queued to Redis
  Celery worker (separate process) picks up task -> sends email -> done

The user gets an instant HTTP response; the email sends in the background.
"""
import os

from celery import Celery

# Tell Celery to use Django's settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')

# Create the Celery app instance
app = Celery('technova_crm')

# Read all CELERY_* settings from Django's settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps (looks for tasks.py in each app)
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """A simple test task — prints the request info. Run: celery -A crm_project call debug_task"""
    print(f'Request: {self.request!r}')
