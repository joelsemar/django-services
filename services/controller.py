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
from services.apps.ops import tasks as ops_tasks


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
        request.initialized = time.time()
        request.request_id = request.POST.get('_request_id') or request.GET.get('_request_id') or ''
        request_method = request.method.upper()

        #django doesn't know PUT
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

        if not mapped_method:
            return HttpResponse("Not Found", status=404)

        method_view = getattr(mapped_method, '_view')

        if not method_view:
            view = self.view(request=request)

        elif method_view.__class__ == type:
            view = method_view(request=request)

        elif  isinstance(method_view, self.view.__class__):
            view = method_view
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

        if '/ops/health' not in request.path and '/map/users' not in request.path and getattr(settings, 'LOG_API_CALLS', False):
            self.log_request(request, response)
            self.log_event(request, response)

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

    def format_errors(self, form):
        return [v[0].replace('This field', k.title()) for k, v in form.errors.items()]

    def log_request(self, request, response):
        queries = connection.queries
        num_queries = len(queries)
        qtime = sum([float(q['time']) for q in queries])
        user_id = 'n/a'
        if request.user.is_authenticated():
            user_id = request.user.id

        self.request_logger.debug('User: %(user_id)s SSN:%(sessionid)s RID:%(request_id)s %(method)s %(path)s '
                                  'ran %(num_queries)s queries in:%(qtime)s seconds. Ttime:%(ttime)s s. --%(status)s ' % {
                                      'request_id': request.request_id or 'n/a',
                                      'num_queries': num_queries, 'qtime': qtime,
                                      'method': getattr( request, 'method', ''),
                                      'ttime': '%.3f' % (time.time() - request.initialized),
                                      'sessionid': request.session._session_key,
                                      'user_id': user_id,
                                      'status': response.status_code,
                                      'path': request.get_full_path()})

    def log_event(self, request, response):
        if 'html' in response._headers['content-type'][1]:
            return

        try:
            body = request.body
        except:
            return

        ops_tasks.log_api_interaction.delay(
              request_id=request.request_id or 'n/a',
              request_method=request.method,
              profile_id=request.user.is_authenticated() and request.user.get_profile().id or None,
              session_id=request.session._session_key or 'n/a',
              host=socket.gethostname(),
              path=request.path,
              query_string=request.META.get('QUERY_STRING', ''),
              request_body=body,
              status_code=response.status_code,
              response_body=response.content,
              when=datetime.datetime.utcnow(),)

    def trace_log(self, message, request):
        if not request.request_id:
            return
        dt = time.time() - request.initialized
        self.request_trace_logger.debug("%s %s after %sms" % (request.request_id, message, dt*1000))

class Resource(object):

    def __init__(self, controller_class):
        self.controller_class = controller_class

    def __call__(self, *args, **kwargs):
        return self.controller_class()(*args, **kwargs)
