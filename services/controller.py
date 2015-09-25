import time
import datetime
import logging
import socket
from django.conf import settings
from django.views.decorators.vary import vary_on_headers
from django.http import HttpResponse, HttpResponseNotAllowed, QueryDict
from django.db import connection
from django.utils.importlib import import_module

from services.utils import generic_exception_handler
from services.view import BaseView
try:
    from services.apps.ops import tasks as ops_tasks
except:
    ops_tasks = None # no celery


class BaseController(object):
    view = BaseView
    callmap = {
        'GET': 'read',
        'POST': 'create',
        'PUT': 'update',
        'DELETE': 'delete'
    }

    request_logger = logging.getLogger('default')
    @vary_on_headers('Authorization')
    def __call__(self, request, *args, **kwargs):
        request_method = request.method.upper()
        if request.META.get('CONTENT_TYPE') == 'application/json':
            self.process_json_body(request)

        #django doesn't know PUT
        else:
            if request_method == "PUT":
                request.PUT = QueryDict(request.raw_post_data)
                request.request_id = request.PUT.get('request_id')
                request.POST = QueryDict({})

            if request_method == "DELETE":
                request.DELETE = QueryDict(request.raw_post_data)
                if not request.DELETE.keys():
                    request.DELETE = QueryDict(request.META['QUERY_STRING'])
                    request.POST = QueryDict({})



        method_name = self.callmap.get(request_method, '')

        if not hasattr(self, method_name):
            return HttpResponseNotAllowed([method for method in self.callmap.keys() if hasattr(self, method)])

        mapped_method = getattr(self, method_name, None)

        if hasattr(mapped_method, '_validator_class'):
            try:
                self.run_validator(request, mapped_method._validator_class)
            except ValidationError as e:
                return  BaseView().add_errors(str(e))

        if not mapped_method:
            return HttpResponse("Not Found", status=404)


        #decorators attach the View class to the method itself as '_view', first look there
        method_view = getattr(mapped_method, '_view', None)

        #or the controller has a default view property
        if not method_view:
            method_view = self.view

        # the user has given us a class @render_with(QuerySetView)
        if method_view.__class__ == type:
            view = method_view(request=request)

        #the user has given us an instantiated instance @render_with(QuerySetView(model_view=MyModelView))
        # we have to reset it and attach the request object to it
        elif  isinstance(method_view, self.view):
            view = method_view
            view.reset(request)

        else:
            raise Exception("Invalid View")
        try:
            response = mapped_method(request, view, *args, **kwargs)

        except Exception, e:
            return self.error_handler(e, request, mapped_method)

        #Allow mapped_method to respond with a view and override ours
        response = response or view

        #user has replaced baseview with something else (likely HttpResponse or HttpREsponseRedirect), we are done
        if not isinstance(response, BaseView):
            return response

        response = self.run_response_middleware(request, response)
        response = response.serialize()

        return response

    def run_response_middleware(self, request, response):
        for mstring in getattr(settings, 'SERVICES_MIDDLEWARE_CLASSES', []):
            module, cls = mstring.rsplit('.', 1)
            module = import_module(module)
            cls = getattr(module, cls)
            response = cls().process_response(request, response)
        return response


    def error_handler(self, e, request, mapped_method):
        return generic_exception_handler(request, e)

    def process_json_body(self, request):
        request_method = request.method.upper()
        try:
            json_data = json.loads(request.body)
            if request_method != 'GET':
                request[request_method] = QueryDict(json_data)
        except:
            raise Exception('Invalid JSON data')


