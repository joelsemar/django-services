

from django.conf.urls import url
from controllers import AliveController

urlpatterns = [url(r'^alive/?', AliveController()),

               ]
