
from django.conf.urls.defaults import patterns
from django.views.generic.simple import direct_to_template
from stapler.decorators import login_required
from stapler.models import Staplerjob

urlpatterns = patterns('stapler.views',
    (r'^login', 'do_login'),
    (r'^logout', 'do_logout'),
    (r'^is_logged_in', 'is_logged_in'),
    (r'^fetch_movement', 'fetch_movement'),
    (r'^commit_movement', 'commit_or_cancel_movement', {'what': 'commit'}),
    (r'^cancel_movement', 'commit_or_cancel_movement', {'what': 'cancel'}),
    (r'^history', 'history'),
    (r'^$', 'index'),
)

urlpatterns += patterns('django.views',
    (r'^mdia/(?P<path>.*)$', 'static.serve', {'document_root': 'media'}),
)
