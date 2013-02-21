#django
from django.conf.urls import patterns, include, url
from django.views.generic.simple import direct_to_template
from django.contrib import admin
#services

#app
from services.apps.docgen.controllers import DocController
admin.autodiscover()

urlpatterns = patterns('',
    url(r'', DocController()),
)
