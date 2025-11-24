import os
from celery import Celery
from django.conf import settings

# Configurar Django settings para Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'entrenador_app.settings')

app = Celery('entrenador_app')

# Usar configuración de Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodescubrir tareas en todas las apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')