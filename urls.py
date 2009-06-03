from django.conf.urls.defaults import *
from django.contrib import databrowse
from django.contrib.auth.decorators import user_passes_test
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^scale/', include('scale.apps.foo.urls.foo')),

    (r'^accounts/$', 'scalereg.auth_helper.views.index'),
    (r'^accounts/profile/$', 'scalereg.auth_helper.views.profile'),
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout'),
    (r'^accounts/password_change/$', 'django.contrib.auth.views.password_change'),
    (r'^accounts/password_change/done/$', 'django.contrib.auth.views.password_change_done'),
    (r'^admin/(.*)', admin.site.root),
#    (r'^admin/', include('django.contrib.admin.urls')),
    (r'^reg6/', include('scalereg.reg6.urls')),
    (r'^reports/', include('scalereg.reports.urls')),
    (r'^speaker_survey/', include('scalereg.speaker_survey.urls')),

    # dummy index page
    (r'^$', 'scalereg.auth_helper.views.index'),

)
