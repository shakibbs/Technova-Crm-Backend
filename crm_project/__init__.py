# Import Celery app so it's available whenever Django starts.
# This ensures @shared_task decorators work and `celery` command finds the app.
from .celery import app as celery_app

__all__ = ('celery_app',)
