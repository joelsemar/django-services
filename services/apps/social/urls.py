from django.conf.urls import patterns, include, url
from django.views.generic.simple import direct_to_template
from services.apps.social.controllers import SocialRegisterController, SocialCallbackController, SocialFriendController, SocialPostController
from django.conf import settings
urlpatterns = patterns('',
   url(r'^register/(?P<network>[\w]+)/?$', SocialRegisterController()),
   url(r'^post/?$', SocialPostController()),
   url(r'^friends/?$', SocialFriendController()),
   url(r'^callback/(?P<network>[\w]+)/?$', SocialCallbackController()),
   url(r'^test/?$', direct_to_template, {'template': 'socialtest.html', 'extra_context': {'baseURL': '/%s/social/register/' % settings.URL_BASE}}),
)
