from django.conf.urls import patterns, include, url
from services.apps.ops.controllers import StatusController, DeployController, HealthController, ErrorReportController
urlpatterns = patterns('',
    url(r'^status/?$', StatusController()),
    url(r'^health/?$', HealthController()),
    url(r'^deploy/?$', DeployController()),
    url(r'^error/?$', ErrorReportController()),
)
