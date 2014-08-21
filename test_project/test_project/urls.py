from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()
from main.controllers import *
from services.apps.docgen import urls as docgen_urls

urlpatterns = patterns('',
    # Examples:
     url(r'^crud/?$', CRUDController()),
     url(r'^blog/?$', BlogPostController()),
     url(r'^blog/(?P<blog_id>[\d]+)/?$', BlogPostController()),
     url(r'^', include(docgen_urls)),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)
