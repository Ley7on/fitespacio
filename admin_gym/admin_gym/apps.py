from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin_gym'

    def ready(self):
        import admin_gym.signals
