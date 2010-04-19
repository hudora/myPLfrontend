# -*- coding: utf-8 -*-

"""URLs for testing myPLfrontend."""

from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/(.*)', 'admin.site.root'),
    (r'^accounts/', include('django.contrib.auth.urls')),
    
    # ensure requests to favicon don't clutter logs
    (r'favicon.ico', 'django.views.generic.simple.redirect_to', {'url': 'http://s.hdimg.net/layout06/favicon.png'}),
    
    # include myplfrontend
    (r'^myplfrontend/', include('myplfrontend.urls')),
    (r'^$', 'django.views.generic.simple.redirect_to', {'url' : '/myplfrontend/'}),
)

# when in development mode, serve static files 'by hand'
# in production the files should be placed at http://s.hdimg.net/myplfrontend/
if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': './static'}),
    )
