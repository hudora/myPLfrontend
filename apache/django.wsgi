import os, site, sys
sys.path.extend(['/usr/local/www/myPLfrontend', '/usr/local/www'])
os.environ['DJANGO_SETTINGS_MODULE'] = 'myPLfrontend.settings'
os.environ['PYTHON_EGG_CACHE'] = '/var/tmp'
site.addsitedir('/usr/local/www/myPLfrontend/pythonenv/lib/python2.5/site-packages')


import django.core.handlers.wsgi

application = django.core.handlers.wsgi.WSGIHandler()
