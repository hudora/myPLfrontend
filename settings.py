# -*- coding: utf-8 -*-
"""
Settings for Django.

Copyright (c) HUDORA. All rights reserved.
"""

# See http://docs.djangoproject.com/en/dev/ref/settings/ for inspiration

import os
import django

# calculated paths for django and the site
# used as starting points for various other paths
DJANGO_ROOT = os.path.dirname(os.path.realpath(django.__file__))
SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

DEBUG = True
TEMPLATE_DEBUG = True
if DEBUG:
    TEMPLATE_STRING_IF_INVALID = "__%s__"
else:
    SEND_BROKEN_LINK_EMAILS = True

MEDIA_URL = 'http://s.hdimg.net/myplfrontend/'
# for development you can use something like this:
# MEDIA_ROOT = './public/'
# MEDIA_URL = '/public/'


SESSION_COOKIE_DOMAIN = 'hudora.biz' # or hudora.de
ROOT_URLCONF = 'urls'
SITE_ID = 2 # intern.hudora.biz


INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.comments',
    'django.contrib.markup',
    #'debug_toolbar',
    'hudoratools',
    'hudjango',

    'myplfrontend',
)


TEMPLATE_DIRS = (
    os.path.join(SITE_ROOT, 'generic_templates'),
    '/usr/local/www/www_intern/generic_templates/',
)


TEMPLATE_CONTEXT_PROCESSORS = (
  'django.core.context_processors.auth',
  'django.core.context_processors.debug',
  'django.core.context_processors.i18n',
  'django.core.context_processors.media',
)


# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
    'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
    'hudjango.middleware.clienttrack.ClientTrackMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)


# This example is all working panels, not all are active with default settings
# DEBUG_TOOLBAR_PANELS = (
#     'debug_toolbar.panels.sql.SQLDebugPanel',
#     'debug_toolbar.panels.headers.HeaderDebugPanel',
#     'debug_toolbar.panels.cache.CacheDebugPanel',
#     'debug_toolbar.panels.profiler.ProfilerDebugPanel',
#     'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
#     'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
#     'debug_toolbar.panels.templates.TemplatesDebugPanel',
#     # If you are using the profiler panel you don't need the timer
#     # 'debug_toolbar.panels.timer.TimerDebugPanel',
# )



#### begin defaults ####

# default settings which should be the same for most Django applications at Hudora
import os

ADMIN_MEDIA_PREFIX = 'http://s.hdimg.net/djangoadmin/1.0.2/'
INTERNAL_IPS = ('127.0.0.1')

TIME_FORMAT = 'H:i'
TIME_ZONE = 'Europe/Amsterdam'
DATETIME_FORMAT = 'Y-m-d H:i:s'
DATE_FORMAT = 'Y-m-d'
USE_I18N = True
LANGUAGE_CODE = 'de-de'
LANGUAGES = (
  ('zh', 'Chinese'),
  ('de', 'German'),
  ('en', 'English'),
)


AUTHENTICATION_BACKENDS = ('hudjango.auth.backends.ZimbraBackend', 'django.contrib.auth.backends.ModelBackend')
LDAP_SERVER_NAME = 'mail.hudora.biz'
SECRET_KEY = 'sua1+khy2x-dojd_+r2j^7$asdfasQ@#$)!v94tpxe-g&_n6xxxv0!f+y'

CACHE_BACKEND = 'memcached://balancer.local.hudora.biz:11211/'
os.environ['PYJASPER_SERVLET_URL'] = 'http://jasper.local.hudora.biz:8080/pyJasper/jasper.py'

COUCHDB_STORAGE_OPTIONS = {'server': "http://couchdb1.local.hudora.biz:5984"}


# for testing
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = 'test.db'

# DATABASE_ENGINE = 'postgresql_psycopg2'           # 'postgresql_psycopg2', 'mysql', 'sqlite3'
# DATABASE_HOST = 'postgresql.local.hudora.biz'
# DATABASE_NAME = 'hudora'
# DATABASE_PASSWORD = 'ge3Xei2O'
# DATABASE_USER = 'hudora'

#SERVER_EMAIL = 'server+django@cybernetics.hudora.biz'
#EMAIL_HOST = 'mail.hudora.biz'
#EMAIL_USE_TLS = True

ADMINS = (
    ('Zwitschr', 'django@cybernetics.hudora.biz'),
    ('HUDORA Operations', 'edv@hudora.de'),
)
ADMINS = ()
MANAGERS = ADMINS
PREPEND_WWW = False
