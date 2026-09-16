
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _split_env_list(value: str | None, default: list[str] | None = None) -> list[str]:
    """Parse une liste depuis une variable d'environnement.

    Args:
        value: La valeur de la variable d'environnement (séparée par virgules).
        default: La valeur par défaut si value est None.

    Returns:
        list: La liste des valeurs nettoyées.
    """
    raw_value = value or (",".join(default or []))
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _build_database_config() -> dict:
    """Construit la configuration de la base de données depuis les variables d'environnement.

    Returns:
        dict: La configuration de la base de données pour Django.
    """
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        parsed = urlparse(database_url)
        if parsed.scheme in {"postgres", "postgresql"}:
            return {
                "default": {
                    "ENGINE": "django.db.backends.postgresql",
                    "NAME": parsed.path.lstrip("/"),
                    "USER": parsed.username or os.environ.get("DB_USER", ""),
                    "PASSWORD": parsed.password or os.environ.get("DB_PASSWORD", ""),
                    "HOST": parsed.hostname or os.environ.get("DB_HOST", "localhost"),
                    "PORT": str(parsed.port or os.environ.get("DB_PORT", "5432")),
                }
            }

    db_name = os.environ.get("DB_NAME")
    db_user = os.environ.get("DB_USER")
    db_password = os.environ.get("DB_PASSWORD")
    if db_name and db_user and db_password and "test" not in sys.argv:
        return {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": db_name,
                "USER": db_user,
                "PASSWORD": db_password,
                "HOST": os.environ.get("DB_HOST", "localhost"),
                "PORT": os.environ.get("DB_PORT", "5432"),
            }
        }

    return {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# SECURITY WARNING: keep the secret key used in production secret!
_INSECURE_DEFAULT_SECRET_KEY = "django-insecure-dev-only-change-me"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", _INSECURE_DEFAULT_SECRET_KEY)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

if not DEBUG and SECRET_KEY == _INSECURE_DEFAULT_SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY doit etre defini avec une vraie valeur secrete "
        "quand DJANGO_DEBUG=0 (production). Generez-en une avec : "
        "python3 -c \"from django.core.management.utils import get_random_secret_key; "
        "print(get_random_secret_key())\""
    )

ALLOWED_HOSTS = _split_env_list(
    os.environ.get("DJANGO_ALLOWED_HOSTS"),
    ["localhost", "127.0.0.1", "0.0.0.0", "[::1]"],
)
CSRF_TRUSTED_ORIGINS = _split_env_list(os.environ.get("CSRF_TRUSTED_ORIGINS"))



INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'django_otp',
    'django_otp.plugins.otp_totp',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'core.middleware.AuditActorMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'groupmanager.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.ui_profile',
            ],
        },
    },
]

WSGI_APPLICATION = 'groupmanager.wsgi.application'

DATABASES = _build_database_config()



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


LANGUAGE_CODE = 'fr'
LANGUAGES = [
    ('fr', 'Français'),
    ('en', 'English'),
    ('ar', 'العربية'),
]

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SECURE_SSL_REDIRECT", "1") == "1"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", "1") == "1"
    SECURE_HSTS_PRELOAD = os.environ.get("DJANGO_SECURE_HSTS_PRELOAD", "1") == "1"
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = "DENY"



STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "core.permissions.StrictDjangoModelPermissions",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": int(os.environ.get("DRF_PAGE_SIZE", "20")),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.environ.get("DRF_THROTTLE_ANON", "60/minute"),
        "user": os.environ.get("DRF_THROTTLE_USER", "240/minute"),
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# drf-spectacular configuration
SPECTACULAR_SETTINGS = {
    "TITLE": "GroupManager API",
    "DESCRIPTION": "API REST pour la gestion de groupes, membres, rencontres et cotisations",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api",
    "SERVERS": [
        {"url": "http://127.0.0.1:8000", "description": "Development server"},
        {"url": "https://groupmanager.example.com", "description": "Production server"},
    ],
    "TAGS": [
        {"name": "Groups", "description": "Gestion des groupes"},
        {"name": "Members", "description": "Gestion des membres"},
        {"name": "Meetings", "description": "Gestion des rencontres"},
        {"name": "Contributions", "description": "Gestion des cotisations"},
        {"name": "Documents", "description": "Gestion des documents"},
        {"name": "Events", "description": "Gestion des événements"},
        {"name": "Audit", "description": "Logs d'audit"},
    ],
}

# Redis Cache Configuration
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100},
        },
        "KEY_PREFIX": "groupmanager",
        "TIMEOUT": 300,  # 5 minutes default
    }
}

# Cache keys for common operations
CACHE_KEYS = {
    "group_list": "groups:list",
    "group_detail": "groups:detail:{id}",
    "member_list": "members:list",
    "member_detail": "members:detail:{id}",
    "dashboard_stats": "dashboard:stats:{user_id}",
    "notification_count": "notifications:count:{user_id}",
}

LOG_LEVEL = os.environ.get("DJANGO_LOG_LEVEL", "INFO")
LOG_DIR = BASE_DIR / "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "groupmanager.log"),
            "maxBytes": 1024 * 1024 * 5,
            "backupCount": 5,
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django.request": {
            "handlers": ["console", "file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "core": {
            "handlers": ["console", "file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
