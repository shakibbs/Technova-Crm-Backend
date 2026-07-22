from django.apps import AppConfig


class CrmConfig(AppConfig):
    name = 'crm'

    def ready(self):
        # Import signals so the task <-> project status sync is registered.
        from . import signals  # noqa: F401
