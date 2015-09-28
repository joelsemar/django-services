from services.controller import BaseController
from services.apps.docgen.server_declaration import ServerDeclaration
from services.decorators import unauthenticated

from django.conf import settings
from django.shortcuts import render


class DocController(BaseController):
    internal = True

    @unauthenticated
    def read(self, request, response):
        """
        Return generated documentation in html format
        API Handler: GET /services/docs
        """
        server_declaration = ServerDeclaration()
        context = {'handlers': server_declaration.handler_list}
        context['servername'] = getattr(settings, 'SERVER_NAME', '')
        admins = getattr(settings, 'ADMINS')
        if admins:
            context['developer_email'] = getattr(settings, 'ADMINS')[0][1]
        else:
            context['developer_email'] = 'admin@example.com'

        return render(request, 'apidocs.html', context)
