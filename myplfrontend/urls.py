from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'django.views.generic.simple.direct_to_template', {'template': 'myplfrontend/index.html'}, name="myplfrontent-index"),
)

# ==========
# = VIEWER =
# ==========
urlpatterns += patterns('myplfrontend.views.viewer',
    (r'^kommiauftrag/$', 'kommiauftrag_list'),
    (r'^kommiauftrag/(?P<kommiauftragnr>\d+)/$', 'kommiauftrag_show'),
    (r'^kommiauftrag/(?P<kommiauftragnr>\d+)/set_priority/$', 'kommiauftrag_set_priority'),
    (r'^kommiauftrag/(?P<kommiauftragnr>\d+)/nullen/$', 'kommiauftrag_nullen'),
    (r'^unit/$', 'unit_list'),
    (r'^unit/(?P<mui>.+)/$', 'unit_show'),
    (r'^bewegungen/$', 'bewegungen'),
    (r'^movements/(?P<movement_id>.*)/storno/$', 'movement_stornieren'),
    (r'^movements/(?P<mid>.*)/$', 'movement_show'),
    (r'^picks/(?P<pickid>.*)/$', 'pick_show'),
    (r'^produkte/$', 'show_articles', {'want_softm': False}),
    (r'^produkte_softm/$', 'show_articles', {'want_softm': True}),
    (r'^produkte/(?P<artnr>.*)/audit/$', 'article_audit'),
    (r'^produkte/(?P<artnr>.*)/$', 'article_detail'),
    
    (r'^info/$', 'lager_info'),
    #(r'^kommischein/(?P<kommid>.*)/$', kommischein_info),
    (r'^plaetze/$', 'lagerplaetze'),
    (r'^plaetze/(?P<location>.+)/$', 'lagerplatz_detail'),
    url(r'^abc/$', 'abc', name="myplfrontend-abc"),
    url(r'^penner/$', 'penner', name="myplfrontend-penner"),
    (r'^komissionierung/infopanel/$', 'info_panel'),
    (r'^artikel_heute/$', 'artikel_heute'),
    (r'^requesttracker/$', 'requesttracker'),
    (r'^softmdifferences/$', 'softmdifferences'),
)

# ========
# = MYPL =
# ========
urlpatterns += patterns('myplfrontend.views.mypl',
    (r'^create_movement/$', 'create_movement'),
)