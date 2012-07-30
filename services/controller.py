from django.views.decorators.vary import vary_on_headers
from django.http import HttpResponse, HttpResponseNotAllowed, QueryDict
from services.utils import generic_exception_handler
from services.view import BaseView


class BaseController(object):
    view = BaseView
    callmap = { 
        'GET': 'read', 
        'POST': 'create',
        'PUT': 'update', 
        'DELETE': 'delete' 
    }
    
    @vary_on_headers('Authorization')
    def __call__(self, request, *args, **kwargs):

        request_method = request.method.upper()

        #django doesn't know PUT
        if request_method == "PUT":
            request.PUT = QueryDict(request.raw_post_data)
            request.POST = QueryDict({})
           
        method_name = self.callmap.get(request_method, '')

        if not hasattr(self, method_name):
            return HttpResponseNotAllowed([method for method in self.callmap.keys() if hasattr(self, method)])

        mapped_method = getattr(self, method_name, None)
        
        if not mapped_method:
            return HttpResponse("Not Found", status=404)
            
        if hasattr(mapped_method, '_view'):
            view = mapped_method._view()
        else:
            view = self.view()

        try:
            response = mapped_method(request, view, *args, **kwargs)
        except Exception, e:
            return self.error_handler(e, request, mapped_method)

        view._request = request
        if not response:
            return view.send()

        if hasattr(response, 'send'):
            return response.send()
          
        return response

    def error_handler(self, e, request, mapped_method):
        return generic_exception_handler(request, e)

    def format_errors(self, form):
        return [v[0].replace('This field', k.title()) for k, v in form.errors.items()]
