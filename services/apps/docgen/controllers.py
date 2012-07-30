from services.controller import BaseController
from services.apps.docgen.server_declaration import ServerDeclaration

from django.conf import settings
from django.views.generic.simple import direct_to_template

from services.apps.docgen.models import APIChangeLogEntry


class DocController(BaseController):
    internal = True

    def read(self, request, response):
        """
        Return generated documentation in html format
        API Handler: GET /services/docs"""
        server_declaration = ServerDeclaration()
        context = {'handlers': server_declaration.handler_list}
        context['servername'] = getattr(settings, 'SERVER_NAME', '')
        context['developer_email'] = getattr(settings, 'ADMINS')[1][1]
        context['changelog_entries'] = APIChangeLogEntry.objects.all()

        return direct_to_template(request, 'apidocs.html', extra_context=context)
