try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # Celery no está disponible, continuar sin él
    pass