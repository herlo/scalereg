from django.conf.urls.defaults import *

from django.contrib.auth.decorators import user_passes_test

urlpatterns = patterns('scalereg.reg6.views',
    url(r'^$', 'index', name='reg6_index'),
)
