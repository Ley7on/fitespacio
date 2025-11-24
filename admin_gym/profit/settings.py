import os
import sys # Agregado para el stream handler en logging
from pathlib import Path
from dotenv import load_dotenv
import pymysql
from storages.backends.gcloud import GoogleCloudStorage
from whitenoise.storage import CompressedManifestStaticFilesStorage

# Instalar el adaptador de MySQL
pymysql.install_as_MySQLdb()

# Cargar variables de entorno local (.env)
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Detección de Entorno ---
IS_CLOUD_RUN = os.getenv('K_SERVICE', None) is not None
IS_APP_ENGINE = os.getenv('GAE_APPLICATION', None) is not None
IS_PRODUCTION = IS_CLOUD_RUN or IS_APP_ENGINE

# --- CONFIGURACIÓN DE SEGURIDAD Y ENTORNO ---
SECRET_KEY = os.environ.get('SECRET_KEY', os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-dev-key-change-in-production'))
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true' and not IS_PRODUCTION

# ALLOWED_HOSTS
if IS_PRODUCTION:
    ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')
else:
    ALLOWED_HOSTS = ['*', '127.0.0.1', '34.176.41.244']

# Application definition
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    # Apps de Terceros (CORREGIDO: Añadido 'storages' y 'crispy_forms')
    'corsheaders',
    'widget_tweaks',
    'crispy_forms',
    'storages',
    
    # Tus Apps
    'admin_gym',
    'trainer_app',
]

# Configuración de Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"
CRISPY_TEMPLATE_PACK = "bootstrap4"

# --- CONFIGURACIÓN DE BASE DE DATOS ---
if IS_PRODUCTION:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'fitspace'),
            'USER': os.environ.get('DB_USER', 'fitspace_user'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '/cloudsql/fitspace-478618:southamerica-west1:free-trial-first-project'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                'charset': 'utf8mb4',
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'fitspace'),
            'USER': os.environ.get('DB_USER', 'dev_user'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'dev_password'),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'), 
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                'charset': 'utf8mb4',
            },
        }
    }

# --- CONFIGURACIÓN DE ARCHIVOS ESTÁTICOS Y MEDIA (CRÍTICO) ---

if IS_PRODUCTION:
    # Google Cloud Storage (GCS) - Recomendado
    GS_BUCKET_NAME = os.environ.get('GS_BUCKET_NAME')
    
    # Backend para archivos estáticos
    STATICFILES_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'
    GS_LOCATION = 'static'
    STATIC_URL = f'https://storage.googleapis.com/{GS_BUCKET_NAME}/{GS_LOCATION}/'
    
    # Backend para archivos multimedia
    DEFAULT_FILE_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'
    MEDIA_LOCATION = 'media'
    MEDIA_URL = f'https://storage.googleapis.com/{GS_BUCKET_NAME}/{MEDIA_LOCATION}/'

    CORS_ALLOW_ALL_ORIGINS = True
    WHITENOISE_AUTOREFRESH = False # Desactiva el refresh si se usa GCS
    
else:
    # Configuración local
    STATIC_URL = '/static/'
    STATIC_ROOT = BASE_DIR / 'staticfiles'
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'


# Configuración base para collectstatic
STATICFILES_DIRS = [
    BASE_DIR / 'static',
    BASE_DIR / 'admin_gym' / 'static',
    BASE_DIR / 'trainer_app' / 'static',
]
# END STATIC CONFIG

# Configuración de email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend' if not IS_PRODUCTION else 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = 'proyectogym12@gmail.com'

# MIDDLEWARE (Tu configuración original)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'admin_gym.middleware.SecurityMiddleware',
    'admin_gym.middleware.AuditMiddleware',
    'admin_gym.middleware.PerformanceMiddleware',
]

ROOT_URLCONF = 'profit.urls'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "admin_gym" / "templates", BASE_DIR / "trainer_app" / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'debug': DEBUG,
        },
    },
]
WSGI_APPLICATION = 'profit.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# RNF-05: Configuraciones de seguridad
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000 if IS_PRODUCTION else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = IS_PRODUCTION
SECURE_HSTS_PRELOAD = IS_PRODUCTION
SECURE_SSL_REDIRECT = IS_PRODUCTION
SESSION_COOKIE_SECURE = IS_PRODUCTION
CSRF_COOKIE_SECURE = IS_PRODUCTION

# Seguridad adicional
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
DATA_UPLOAD_MAX_MEMORY_SIZE = 2621440
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440

# Content Security Policy
CSP_DEFAULT_SRC = ["'self'"]
CSP_SCRIPT_SRC = ["'self'", "'unsafe-inline'"]
CSP_STYLE_SRC = ["'self'", "'unsafe-inline'"]
CSP_IMG_SRC = ["'self'", "data:"]
CSP_FONT_SRC = ["'self'"]

# Prevenir clickjacking
X_FRAME_OPTIONS = 'DENY'

# Validación de entrada
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000
FILE_UPLOAD_PERMISSIONS = 0o644

# Configuración de sesiones
SESSION_COOKIE_SECURE = IS_PRODUCTION
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_SAMESITE = 'Lax' if IS_PRODUCTION else 'Strict'
SESSION_SAVE_EVERY_REQUEST = True

# CSRF
CSRF_COOKIE_SECURE = IS_PRODUCTION
CSRF_COOKIE_HTTPONLY = True
if IS_PRODUCTION:
    CSRF_TRUSTED_ORIGINS = [f'https://{host}' for host in ALLOWED_HOSTS if host not in ['localhost', '127.0.0.1']]

# RNF-03: Configuración de base de datos para escalabilidad
DATABASE_CONNECTION_POOLING = True
DATABASES['default']['CONN_MAX_AGE'] = 60

# RNF-02: Configuración de cache para operación offline
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'gym-cache',
        'TIMEOUT': 600,
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}

# Configuración de archivos media (para QR codes)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# RNF-01: Configuración de timeout para requests
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880

# --- LOGGING (CORRECCIÓN CRÍTICA PARA CLOUD RUN) ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        # Handler en producción (Cloud Run): logs a la consola (stdout)
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'verbose',
        },
        # Handler en desarrollo (Fallback si el sistema no es Cloud Run)
        'file_dev': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'gym.log',
            'formatter': 'verbose',
        },
        'security_file_dev': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'] if IS_PRODUCTION else ['file_dev', 'console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'] if IS_PRODUCTION else ['file_dev', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'admin_gym.security': {
            'handlers': ['console'] if IS_PRODUCTION else ['security_file_dev'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
# La creación manual de directorios de log ('logs' folder) debe hacerse fuera de la compilación
if not IS_PRODUCTION and not os.path.exists(BASE_DIR / 'logs'):
     os.makedirs(BASE_DIR / 'logs')
# END LOGGING CONFIG

# CORS Configuration
if IS_PRODUCTION:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = [f'https://{host}' for host in ALLOWED_HOSTS if host not in ['localhost', '127.0.0.1']]
    CORS_ALLOW_CREDENTIALS = True
else:
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type', 'dnt', 'origin', 
    'user-agent', 'x-csrftoken', 'x-requested-with',
]
# END CORS CONFIG

# Configuración de backup automático
BACKUP_ENABLED = True
BACKUP_SCHEDULE = '0 2 * * *'

# Configuración de backends de autenticación
AUTHENTICATION_BACKENDS = [
    'admin_gym.backends.RUTAuthenticationBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Manejadores de error personalizados
handler404 = 'admin_gym.error_handlers.handler404'
handler500 = 'admin_gym.error_handlers.handler500'
handler403 = 'admin_gym.error_handlers.handler403'

# RNF-07: Configuraciones personalizables
GYM_CONFIG = {
    'HORARIO_APERTURA': '06:00',
    'HORARIO_CIERRE': '23:00',
    'CAPACIDAD_MAXIMA': 500,
    'QR_OFFLINE_TIMEOUT': 600,
    'NOTIFICACIONES_ACTIVAS': True,
    'RACHA_MINIMA_NOTIFICACION': 7,
}
