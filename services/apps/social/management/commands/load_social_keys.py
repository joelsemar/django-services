import os
from django.core.management.base import NoArgsCommand
from optparse import make_option
from django.conf import settings
from services.apps.social.models import SocialNetwork

class Command(NoArgsCommand):

    def handle_noargs(self, **options):
        api_key = getattr(settings, 'LI_API_KEY');
        app_secret = getattr(settings, 'LI_SECRET_KEY');
        if not api_key:
            print "No api key found in settings"
            return

        if not app_secret:
            print "No api key found in settings"
            return

        try:
            linkedin  = SocialNetwork.objects.get(name="linkedin")
        except SocialNetwork.DoesNotExist:
            print "Missing social network fixtures"

        linkedin.api_key = api_key
        linkedin.app_secret = app_secret
        linkedin.save()

