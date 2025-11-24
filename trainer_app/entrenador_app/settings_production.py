import os
from .settings import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# Allowed hosts for Vercel
ALLOWED_HOSTS = [
    '.vercel.app',
    '.now.sh',
    'localhost',
    '127.0.0.1',
    'fitspace-gym.vercel.app',  # Tu dominio específico
]

# Secret key from environment
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-this-in-production')

# Database for production (using SQLite for simplicity)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/tmp/db.sqlite3',
    }
}

# Ensure database directory exists
os.makedirs('/tmp', exist_ok=True)

# Static files configuration for Vercel
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_build', 'static')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# CORS settings (if needed)
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = [
    "https://fitspace-gym.vercel.app",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Add CORS middleware
if 'corsheaders.middleware.CorsMiddleware' not in MIDDLEWARE:
    MIDDLEWARE.insert(0, 'corsheaders.middleware.CorsMiddleware')

# Disable migrations in production (for demo purposes)
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

# Enable migrations in production for initial setup
# MIGRATION_MODULES = DisableMigrations()

# PWA Settings
PWA_APP_NAME = 'FitSpace'
PWA_APP_DESCRIPTION = 'Sistema de Gestión de Gimnasio'
PWA_APP_THEME_COLOR = '#007bff'
PWA_APP_BACKGROUND_COLOR = '#0f0f0f'
PWA_APP_DISPLAY = 'standalone'
PWA_APP_SCOPE = '/'
PWA_APP_ORIENTATION = 'any'
PWA_APP_START_URL = '/'
PWA_APP_ICONS = [
    {
        'src': '/static/icons/logo.jpg',
        'sizes': '160x160'
    }
]
PWA_SERVICE_WORKER_PATH = os.path.join(BASE_DIR, 'static', 'service-worker.js')

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}