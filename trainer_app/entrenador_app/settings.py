import os
from pathlib import Path
from django.core.management.utils import get_random_secret_key
from dotenv import load_dotenv

# Intentar importar pymysql solo si está disponible
try:
    import pymysql
    pymysql.install_as_MySQLdb()
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Detectar entorno de producción
IS_CLOUD_RUN = os.getenv('K_SERVICE', None) is not None
IS_APP_ENGINE = os.getenv('GAE_APPLICATION', None) is not None
IS_PRODUCTION = IS_CLOUD_RUN or IS_APP_ENGINE

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', get_random_secret_key())

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true' if not IS_PRODUCTION else False

if IS_PRODUCTION:
    ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')
else:
    ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'crispy_bootstrap5',
    'entrenador',
    'alumno',
    'entrenador_app',
    'pwa',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Debe estar justo después de SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'entrenador_app.redirect_middleware.RootRedirectMiddleware',
]



ROOT_URLCONF = 'entrenador_app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',  # Agrega esta línea
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'entrenador_app.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# Configuración de base de datos
if IS_PRODUCTION:
    # Running on Google Cloud (App Engine or Cloud Run) with Cloud SQL
    if MYSQL_AVAILABLE:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.mysql',
                'NAME': os.getenv('DB_NAME', 'fitspace'),
                'USER': os.getenv('DB_USER', 'free-trial-first-project'),
                'PASSWORD': os.getenv('DB_PASSWORD', ''),
                'HOST': os.getenv('DB_HOST', '/cloudsql/fitspace-478618:southamerica-west1:free-trial-first-project'),
                'PORT': os.getenv('DB_PORT', '3306'),
                'OPTIONS': {
                    'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                    'charset': 'utf8mb4',
                },
            }
        }
    else:
        # Fallback a SQLite en producción si MySQL no disponible (no recomendado)
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
elif MYSQL_AVAILABLE and os.getenv('USE_MYSQL', 'True').lower() == 'true':
    # Base de datos Google Cloud SQL con IP pública (desarrollo local)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.getenv('DB_NAME', 'fitspace'),
            'USER': os.getenv('DB_USER', 'free-trial-first-project'),
            'PASSWORD': os.getenv('DB_PASSWORD', 'Hyf(/k"8TB[{89FJ'),
            'HOST': os.getenv('DB_HOST', '34.176.41.244'),
            'PORT': os.getenv('DB_PORT', '3306'),
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                'charset': 'utf8mb4',
            },
        }
    }
else:
    # Usar SQLite como fallback
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }





# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / "static"]

# WhiteNoise configuration para servir archivos estáticos en producción
if IS_PRODUCTION:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
else:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage' 

# Media files (uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Security Settings - ISO 27001 Compliance
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000 if IS_PRODUCTION else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = IS_PRODUCTION
SECURE_SSL_REDIRECT = IS_PRODUCTION
SESSION_COOKIE_SECURE = IS_PRODUCTION
CSRF_COOKIE_SECURE = IS_PRODUCTION
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = False  # Cambiar a True en producción
SESSION_COOKIE_SECURE = False  # Cambiar a True en producción
CSRF_COOKIE_SECURE = False  # Cambiar a True en producción
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # Permitir acceso desde JS para ngrok
SESSION_COOKIE_SAMESITE = 'Lax'  # Más permisivo para ngrok
CSRF_COOKIE_SAMESITE = 'Lax'  # Más permisivo para ngrok

# Configuración específica para ngrok
CSRF_TRUSTED_ORIGINS = [
    'https://*.ngrok.io',
    'https://*.ngrok-free.app',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    # If your frontend runs on a different port (e.g. Vite/React dev server)
    # include it here with scheme and port so Django accepts Referer from it.
    'http://localhost:5173',
]

# Permitir CSRF desde cualquier origen en desarrollo
if DEBUG:
    CSRF_COOKIE_DOMAIN = None
    CSRF_USE_SESSIONS = False
    # Vista temporal para depuración de fallos CSRF
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 3600  # 1 hour

# Logging Configuration - ISO 9001 & 27001 Compliance
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'entrenador_app': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Authentication
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# Password validation - Enhanced for ISO 25010 & 27001
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# PWA
PWA_APP_NAME = 'ENTRENADOR'
PWA_APP_DESCRIPTION = 'FIT SPACE TRAINER'
PWA_APP_THEME_COLOR = '#007bff'
PWA_APP_BACKGROUND_COLOR = '#3104d3'
PWA_APP_DISPLAY = 'standalone'
PWA_APP_SCOPE = '/'
PWA_APP_START_URL = '/'
PWA_APP_ORIENTATION = 'portrait'
PWA_APP_ICONS = [
    { 'src': '/static/icons/logo.jpg', 'sizes': '192x192', 'type': 'image/jpeg' },
    { 'src': '/static/icons/logo.jpg', 'sizes': '512x512', 'type': 'image/jpeg' },
]
PWA_APP_SHORTCUT_ICON = '/static/icons/logo.jpg'
PWA_SERVICE_WORKER_PATH = BASE_DIR / 'static' / 'service-worker.js'

# Create logs directory
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Isolate cookies to avoid collision with admin_app when both run on the same host
# This lets you be logged in to both apps in the same browser simultaneously.
SESSION_COOKIE_NAME = 'trainer_sessionid'
# Use the default CSRF cookie name to avoid cross-app confusion and JS assumptions
# (many templates and scripts expect the cookie name 'csrftoken'). If you do need
# per-app CSRF isolation, re-introduce a custom name but make sure front-end
# code reads the correct cookie name.
CSRF_COOKIE_NAME = 'csrftoken'

# Manejadores de error personalizados
handler404 = 'entrenador_app.error_handlers.handler404'
handler500 = 'entrenador_app.error_handlers.handler500'
handler403 = 'entrenador_app.error_handlers.handler403'

# Custom view to log CSRF failures and aid debugging in development
CSRF_FAILURE_VIEW = 'entrenador_app.error_handlers.csrf_failure'

# Content Security Policy
CSP_DEFAULT_SRC = ["'self'"]
CSP_SCRIPT_SRC = ["'self'", "'unsafe-inline'"]
CSP_STYLE_SRC = ["'self'", "'unsafe-inline'"]
CSP_IMG_SRC = ["'self'", "data:"]
CSP_FONT_SRC = ["'self'"]

# Validación de entrada
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000
FILE_UPLOAD_PERMISSIONS = 0o644

# Email Configuration
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'FitSpace <proyectogym12@gmail.com>')

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE


