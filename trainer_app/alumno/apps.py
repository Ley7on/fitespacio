from django.apps import AppConfig


class AlumnoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'alumno'

    def ready(self):
        # Import signals to ensure receivers are connected
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
