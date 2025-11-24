"""
Local development settings for FitSpace
Use SQLite for local development and testing
"""

from .settings import *

# Override database settings for local development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Debug settings
DEBUG = True
ALLOWED_HOSTS = ['*']

# Disable HTTPS requirements for local development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Simplified logging for development
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'entrenador_app': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Create logs directory
import os
os.makedirs(BASE_DIR / 'logs', exist_ok=True)