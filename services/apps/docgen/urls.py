#django
from django.conf.urls import patterns, include, url
from django.views.generic.simple import direct_to_template
from django.contrib import admin
#services

#app
from services.apps.docgen.controllers import DocController
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'cwnserver.views.home', name='home'),
    # url(r'^cwnserver/', include('cwnserver.foo.urls')),
    url(r'', DocController()),
)
