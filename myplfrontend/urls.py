from django.conf.urls.defaults import *
from myplfrontend.views import lager_info, article_detail
from myplfrontend.views import article_audit, lagerplatz_detail, lagerplaetze
from myplfrontend.views import abc, index
from myplfrontend.views import penner, info_panel
from myplfrontend.views import artikel_heute#, kommischein_info

urlpatterns = patterns('myplfrontend.views',
    (r'^$', index),
    (r'^kommiauftrag/$', 'kommiauftrag_list'),
    (r'^kommiauftrag/(?P<kommiauftragnr>\d+)/$', 'kommiauftrag_show'),
    (r'^kommiauftrag/(?P<kommiauftragnr>\d+)/set_priority/$', 'kommiauftrag_set_priority'),
    (r'^kommiauftrag/(?P<kommiauftragnr>\d+)/nullen/$', 'kommiauftrag_nullen'),
    (r'^unit/$', 'unit_list'),
    (r'^unit/(?P<mui>.+)/$', 'unit_show'),
    (r'^bewegungen/$', 'bewegungen'),
    (r'^movements/(?P<mid>.*)/$', 'movement_show'),
    (r'^picks/(?P<pickid>.*)/$', 'pick_show'),
    (r'^produkte/$', 'show_articles', {'want_softm': False}),
    (r'^produkte_softm/$', 'show_articles', {'want_softm': True}),
    (r'^produkte/(?P<artnr>.*)/audit/$', 'article_audit'),
    (r'^produkte/(?P<artnr>.*)/$', 'article_detail'),
    
    (r'^info/$', lager_info),
    #(r'^kommischein/(?P<kommid>.*)/$', kommischein_info),
    (r'^plaetze/$', lagerplaetze),
    (r'^plaetze/(?P<location>.+)/$', lagerplatz_detail),
    (r'^abc/$', abc),
    (r'^penner/$', penner),
    (r'^komissionierung/infopanel/$', info_panel),
    (r'^artikel_heute/$', artikel_heute),
)
