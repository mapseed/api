from os import environ
import raven
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG
SHOW_DEBUG_TOOLBAR = DEBUG
DEBUG_TOOLBAR_PATCH_SETTINGS = False

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

###############################################################################
#
# Server Configuration
#

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['*']
SECRET_KEY = 'pbv(g=%7$$4rzvl88e24etn57-%n0uw-@y*=7ak422_3!zrc9+'
SITE_ID = 1

# How long to keep api cache values. Since the api will invalidate the cache
# automatically when appropriate, this can (and should) be set to something
# large.
# NOTE(goldpbear): We have disabled caching for now, pending a further
# investigation into its effects on newly-created places and comments.
# See: https://github.com/jalMogo/mgmt/issues/112
API_CACHE_TIMEOUT = 1

# Where should the user be redirected to when they visit the root of the site?
ROOT_REDIRECT_TO = 'api-root'

# Ensure forwards from the proxy that originate as HTTPS are passed through and
# processed by Django as HTTPS requests
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

USE_X_FORWARDED_HOST = True

###############################################################################
#
# Time Zones
#

TIME_ZONE = 'Universal'
USE_TZ = True

###############################################################################
#
# Internationalization and Localization
#

LANGUAGE_CODE = 'en-us'
USE_I18N = True
USE_L10N = True

###############################################################################
#
# Templates and Static Assets
#
from os.path import dirname, normpath, abspath, join as pathjoin

MEDIA_ROOT = ''
MEDIA_URL = ''

PROJECT_ROOT = normpath(dirname(__file__))
STATIC_ROOT = abspath(pathjoin(dirname(__file__), '..', '..', 'static'))
STATIC_URL = '/static/'
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
STATICFILES_DIRS = ()

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)
TEMPLATE_DIRS = ()

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
    'django.core.context_processors.request',
)

ATTACHMENT_STORAGE = 'django.core.files.storage.FileSystemStorage'

###############################################################################
#
# Django Rest Framework
#
REST_FRAMEWORK = {
    'PAGINATE_BY': 100,
    'PAGINATE_BY_PARAM': 'page_size',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'oauth2_provider.ext.rest_framework.OAuth2Authentication',
    )
}

###############################################################################
#
# Request/Response processing
#

WSGI_APPLICATION = 'project.wsgi.application'
ROOT_URLCONF = 'project.urls'

MIDDLEWARE_CLASSES = (
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'remote_client_user.middleware.RemoteClientMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'sa_api_v2.middleware.RequestTimeLogger',
    'sa_api_v2.middleware.RequestBodyLogger',
)

# We only use the CORS Headers app for oauth. The Shareabouts API resources
# have their own base view that handles CORS headers.
CORS_URLS_REGEX = r'^/api/v\d+/users/oauth2/.*$'
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True


###############################################################################
#
# Pluggable Applications
#

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',

    # =================================
    # 3rd-party reusaple apps
    # =================================
    'rest_framework',
    'django_nose',
    'storages',
    'social_django',
    'raven.contrib.django.raven_compat',
    'django_ace',
    'django_object_actions',
    'djcelery',
    'loginas',

    # OAuth
    # 'provider',
    # 'provider.oauth2',
    # testing switch to django-oauth-toolkit
    'oauth2_provider',
    'corsheaders',

    # =================================
    # Project apps
    # =================================
    'beta_signup',
    'sa_api_v2',
    'remote_client_user',

    # GeoDjango comes last so that we can override its admin templates.
    'django.contrib.gis',
)


###############################################################################
#
# Background task processing
#

CELERY_RESULT_BACKEND='djcelery.backends.database:DatabaseBackend'
CELERY_ACCEPT_CONTENT = ['json', 'msgpack', 'yaml', 'pickle']


###############################################################################
#
# Authentication
#

AUTHENTICATION_BACKENDS = (
    # See http://django-social-auth.readthedocs.org/en/latest/configuration.html
    # for list of available backends.
    #'social.backends.facebook.FacebookOAuth2',
    'social_core.backends.twitter.TwitterOAuth',
    'sa_api_v2.auth_backends.NoRedirectStateFacebookOAuth2',
    'social_core.backends.google.GoogleOAuth2',
    'sa_api_v2.auth_backends.CachedModelBackend',
)

OAUTH2_PROVIDER_APPLICATION_MODEL = 'oauth2_provider.Application'
AUTH_USER_MODEL = 'sa_api_v2.User'
SOCIAL_AUTH_USER_MODEL = 'sa_api_v2.User'
SOCIAL_AUTH_PROTECTED_USER_FIELDS = ['email',]

SOCIAL_AUTH_FACEBOOK_EXTRA_DATA = ['name', 'picture', 'about']
SOCIAL_AUTH_TWITTER_EXTRA_DATA = ['name', 'description', 'profile_image_url_https']
SOCIAL_AUTH_GOOGLE_OAUTH2_EXTRA_DATA = ['name', 'image', 'aboutMe']

# Explicitly request the following extra things from facebook
SOCIAL_AUTH_FACEBOOK_PROFILE_EXTRA_PARAMS = {'fields': 'id,name,picture.width(96).height(96),first_name,last_name,about'}

SOCIAL_AUTH_LOGIN_ERROR_URL = 'remote-social-login-error'


################################################################################
#
# Testing and administration
#

# Tests (nose)
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
TESTS_MIGRATE = True
# MIGRATION_MODULES = {
#     'oauth2': 'ignore',
#     'djcelery': 'ignore',
# }


# Debug toolbar
def custom_show_toolbar(request):
    return SHOW_DEBUG_TOOLBAR

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': 'project.settings.custom_show_toolbar',
    'INTERCEPT_REDIRECTS': False
}

INTERNAL_IPS = ('127.0.0.1',)
DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.profiling.ProfilingPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.cache.CachePanel',  # Disabled by default
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
)
# (See the very end of the file for more debug toolbar settings)


###############################################################################
# Logging Configuration
###############################################################################

# disable Django's own log configuration mechanism:
LOGGING_CONFIG = None
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(name)s: %(message)s ' +
            '%(process)d %(thread)d'
        },
        'moderate': {
            'format': '%(levelname)s %(asctime)s %(name)s: %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'moderate'
        },
        'sentry': {
            'level': 'INFO',
            'class': 'raven.contrib.django.raven_compat.handlers.' +
            'SentryHandler',
            'formatter': 'verbose',
            'tags': {'custom-tag': 'x'},
        },
    },
    'loggers': {
        'root': {
            'handlers': ['console', 'sentry'],
            'level': 'WARNING'
        },
        'django.request': {
            'handlers': ['console', 'sentry'],
            'level': 'ERROR',
            'propagate': True,
        },
        'sa_api_v2': {
            'handlers': ['console', 'sentry'],
            'level': 'INFO',
            'propagate': True,
        },

        'django.db.backends': {
            'handlers': ['console', 'sentry'],
            'level': 'DEBUG',
            'propagate': True,
        },

        'ms_api.request': {
            'handlers': ['console', 'sentry'],
            'level': 'INFO',
            'propagate': True,
        },

        'utils.request_timer': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },

        'storages': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },

        'redis_cache': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}

# setting the log configuration explicitly ourselves using
# the Python logging APIs:
import logging.config
logging.config.dictConfig(LOGGING)


# Sentry config:
if 'SENTRY_DSN' in environ:
    RAVEN_CONFIG = {
        'dsn': environ['SENTRY_DSN'],
        'release': raven.fetch_git_sha(os.path.dirname(os.pardir)),
        'CELERY_LOGLEVEL': logging.INFO
    }

##############################################################################
# Environment loading

if 'DATABASE_URL' in environ:
    import dj_database_url
    # NOTE: Be sure that your DATABASE_URL has the 'postgis://' scheme.
    DATABASES = {'default': dj_database_url.config()}
    DATABASES['default']['ENGINE'] = 'django.contrib.gis.db.backends.postgis'

if 'DEBUG' in environ:
    DEBUG = (environ['DEBUG'].lower() == 'true')
    TEMPLATE_DEBUG = DEBUG
    SHOW_DEBUG_TOOLBAR = DEBUG


# Look for the following redis environment variables, in order
for REDIS_URL_ENVVAR in ('REDIS_URL', 'OPENREDIS_URL'):
    if REDIS_URL_ENVVAR in environ: break
else:
    REDIS_URL_ENVVAR = None

if REDIS_URL_ENVVAR:
    import django_cache_url
    CACHES = {'default': django_cache_url.config(env=REDIS_URL_ENVVAR)}

    # Django sessions
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"

    # Celery broker
    BROKER_URL = environ[REDIS_URL_ENVVAR].strip('/') + '/1'

if all([key in environ for key in ('SHAREABOUTS_AWS_KEY',
                                   'SHAREABOUTS_AWS_SECRET',
                                   'SHAREABOUTS_AWS_BUCKET')]):
    AWS_ACCESS_KEY_ID = environ['SHAREABOUTS_AWS_KEY']
    AWS_SECRET_ACCESS_KEY = environ['SHAREABOUTS_AWS_SECRET']
    AWS_STORAGE_BUCKET_NAME = environ['SHAREABOUTS_AWS_BUCKET']
    AWS_QUERYSTRING_AUTH = False
    AWS_PRELOAD_METADATA = True

    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
    ATTACHMENT_STORAGE = DEFAULT_FILE_STORAGE

if 'SHAREABOUTS_TWITTER_KEY' in environ \
        and 'SHAREABOUTS_TWITTER_SECRET' in environ:
    SOCIAL_AUTH_TWITTER_KEY = environ['SHAREABOUTS_TWITTER_KEY']
    SOCIAL_AUTH_TWITTER_SECRET = environ['SHAREABOUTS_TWITTER_SECRET']

if 'SHAREABOUTS_FACEBOOK_KEY' in environ \
        and 'SHAREABOUTS_FACEBOOK_SECRET' in environ:
    SOCIAL_AUTH_FACEBOOK_KEY = environ['SHAREABOUTS_FACEBOOK_KEY']
    SOCIAL_AUTH_FACEBOOK_SECRET = environ['SHAREABOUTS_FACEBOOK_SECRET']


if 'SHAREABOUTS_ADMIN_EMAIL' in environ:
    ADMINS = (
        ('Shareabouts API Admin', environ.get('SHAREABOUTS_ADMIN_EMAIL')),
    )

if 'CONSOLE_LOG_LEVEL' in environ:
    LOGGING['handlers']['console']['level'] = environ.get('CONSOLE_LOG_LEVEL')

##############################################################################
# Local GEOS/GDAL installations (for Heroku)

import os.path

if os.path.exists('/app/.geodjango/geos/lib/libgeos_c.so'):
    GEOS_LIBRARY_PATH = '/app/.geodjango/geos/lib/libgeos_c.so'

if os.path.exists('/app/.geodjango/gdal/lib/libgdal.so'):
    GDAL_LIBRARY_PATH = '/app/.geodjango/gdal/lib/libgdal.so'

TEMPLATES = [
   {
       'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

##############################################################################
# Local settings overrides
# ------------------------
# Override settings values by importing the local_settings.py module.

try:
    from .local_settings import *
except ImportError:
    pass

##############################################################################
# More background processing
#

try:
    BROKER_URL
except NameError:
    BROKER_URL = 'django://'

if BROKER_URL == 'django://':
    INSTALLED_APPS += ('kombu.transport.django', )


##############################################################################
# Debug Toolbar
# ------------------------
# Do this after all the settings files have been processed, in case the
# SHOW_DEBUG_TOOLBAR setting is set.

if SHOW_DEBUG_TOOLBAR:
    INSTALLED_APPS += ('debug_toolbar',)
    MIDDLEWARE_CLASSES = (
        MIDDLEWARE_CLASSES[:2] +
        ('debug_toolbar.middleware.DebugToolbarMiddleware',) +
        MIDDLEWARE_CLASSES[2:]
    )
