from django.apps import AppConfig


class EntrenadorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'entrenador'

    def ready(self):
        """Registrar signals cuando la app esté lista"""
        import entrenador.rutina_signals  # noqa
