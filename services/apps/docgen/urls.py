# django
from django.conf.urls import url
from django.contrib import admin
# services

# app
from services.apps.docgen.controllers import DocController
admin.autodiscover()

urlpatterns = [
    url(r'', DocController()),
]
