import logging
import json
import inspect
from django.conf import settings
from django.http import HttpResponse, HttpResponseNotAllowed, QueryDict
from django.utils.importlib import import_module
from django.db.models import Model as DjangoModel
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.fields import DateTimeField, DateField

from services.utils import generic_exception_handler, un_camel_dict, un_camel, default_time_parse
from services.view import BaseView
from services.models import ModelDTO
try:
    from services.apps.ops import tasks as ops_tasks
except:
    ops_tasks = None  # no celery


class BaseController(object):
    view = BaseView
    callmap = {
        'GET': 'read',
        'POST': 'create',
        'PUT': 'update',
        'DELETE': 'delete'
    }

    request_logger = logging.getLogger('default')

    def __call__(self, request, *args, **kwargs):

        request.camel_case = request.META.get("X-SERVICES-CAMEL") != None or request.GET.get("_camel")
        self.fix_delete_and_put(request)
        self.build_payload(request)

        mapped_method = self.get_mapped_method(request)
        if not mapped_method:
            return HttpResponse("Not Found", status=404)

        auth_result = self.auth_check(request, mapped_method)

        if auth_result:
            return auth_result

        try:
            if self.has_body_param(mapped_method):
                body_param = self.build_body_param(request, mapped_method)
                if body_param:
                    args = self.insert_into_arglist(args, body_param)

            if self.has_updates_param(mapped_method):
                self.build_updates_param(request, mapped_method, kwargs)

            if self.uses_entity(mapped_method):
                self.set_entity_param(request, mapped_method, kwargs)

            kwargs = self.set_query_params_to_kwargs(request, mapped_method, kwargs)

        except EntityNotFoundException as e:
            return self.view().not_found(str(e)).serialize()

        view = self.get_view(request, mapped_method)
        if view:
            args = self.insert_into_arglist(args, view)

        args = self.insert_into_arglist(args, request)

        try:
            response = mapped_method(*args, **kwargs)

        except Exception, e:
            return self.error_handler(e, request, mapped_method)

        # Allow mapped_method to respond with a view and override ours
        response = response or view

        # user has replaced baseview with something else (likely HttpResponse or HttpResponseRedirect), we are done
        if not isinstance(response, BaseView):
            return response

        response = self.run_response_middleware(request, response)
        return response.serialize()

    def run_response_middleware(self, request, response):
        for mstring in getattr(settings, 'SERVICES_MIDDLEWARE_CLASSES', []):
            module, cls = mstring.rsplit('.', 1)
            module = import_module(module)
            cls = getattr(module, cls)
            response = cls().process_response(request, response)
        return response

    def error_handler(self, e, request, mapped_method):
        return generic_exception_handler(request, e)

    def build_payload(self, request):
        content_type = request.META.get("CONTENT_TYPE", "application/json")
        if content_type == 'application/json':
            try:
                request.payload = json.loads(request.body)
            except Exception as e:
                raise Exception('Invalid JSON data ' + e.message)

        elif content_type == "application/x-www-form-urlencoded":
            request.payload = dict(getattr(request, request.method.upper, {}))

        if getattr(request, 'camel_case', False):
            request.payload = un_camel_dict(request.payload)

    def get_view(self, request, mapped_method):
        # decorators attach the View class to the method itself as '_view', first look there
        method_view = getattr(mapped_method, '_view', None)

        # or the controller has a default view property
        if not method_view:
            method_view = self.view

        if not method_view:
            return None

        # the user has given us a class @render_with(QuerySetView)
        if method_view.__class__ == type and BaseView in inspect.getmro(method_view):
            view = method_view(request=request)

        # the user has given us an instantiated instance @render_with(QuerySetView(model_view=MyModelView))
        # we have to reset it and attach the request object to it
        elif isinstance(method_view, self.view):
            view = method_view
            view.reset(request)

        else:
            raise Exception("Invalid view argument %s, must extend BaseView" % method_view)

        return view

    def build_body_param(self, request, mapped_method):
        body_param_class = getattr(mapped_method, '_body_param_class', None)
        hidden_fields = getattr(body_param_class, '_hides', [])
        if not body_param_class:
            return None

        if not request.payload:
            return None

        if DjangoModel in inspect.getmro(body_param_class):
            return self.build_model_body_payload(request, mapped_method, body_param_class)

        body_param = body_param_class()
        provided_fields = [f for f in dir(body_param) if not f.startswith("_")]

        # just using a basic Payload object, no properties defined
        if not provided_fields:
            for key, value in request.payload.items():
                setattr(body_param, key, value)

        # here our payload class has properties defined, we just grab those
        else:
            for field in provided_fields:
                if field in hidden_fields:
                    continue
                if request.payload.get(field):
                    setattr(body_param, field, request.payload.get(field))
                else:
                    # use the Class.prop value as default
                    setattr(body_param, field, getattr(body_param_class, field))

        return body_param

    def build_model_body_payload(self, request, mapped_method, body_param_class):
        body_param = body_param_class()
        self.update_model_instance_with_payload(body_param, request.payload)
        return body_param

    def build_updates_param(self, request, method, kwargs):
        model_instance = self.get_model_instance(request, method, "_updates_model", "_updates_model_arg", kwargs)
        self.update_model_instance_with_payload(model_instance, request.payload)
        updates_model_arg = getattr(method, '_updates_model_arg')
        kwargs[updates_model_arg] = model_instance

    def update_model_instance_with_payload(self, model_instance, payload):
        if model_instance and payload:
            for field in model_instance._meta.fields:
                if field.primary_key:
                    continue
                field_attname = field.attname
                field_name = field.name
                val = payload.get(field_name, payload.get(field_attname))
                if field.__class__ in (DateTimeField, DateField):
                    val = default_time_parse(val)
                if field.name in payload.keys():
                    setattr(model_instance, field.attname, val)

    def set_entity_param(self, request, method, kwargs):
        model_instance = self.get_model_instance(request, method, "_entity_model", "_entity_model_arg", kwargs)
        if model_instance:
            entity_model_arg = getattr(method, '_entity_model_arg')
            kwargs[entity_model_arg] = model_instance

    def get_model_instance(self, request, method, model_arg_type, arg_type, kwargs):
        if hasattr(method, model_arg_type):
            model_class = getattr(method, model_arg_type)
            bases = inspect.getmro(model_class)
            if ModelDTO in bases:
                # Muhahahahah!!!
                model_class = bases[bases.index(ModelDTO) + 1]
            model_arg = getattr(method, arg_type)
            try:
                if kwargs.get(model_arg):
                    return model_class.objects.get(id=kwargs[model_arg])
                else:
                    return model_class.objects.get(user=request.user)
            except ObjectDoesNotExist:
                raise EntityNotFoundException(model_arg + " not found.")

    def fix_delete_and_put(self, request):
        if request.method == "put":
            request.PUT = QueryDict(request.raw_post_data)
            request.request_id = request.PUT.get('request_id')
            request.POST = QueryDict({})

        if request.method == "delete":
            request.DELETE = QueryDict(request.raw_post_data)
            if not request.DELETE.keys():
                request.DELETE = QueryDict(request.META['QUERY_STRING'])
                request.POST = QueryDict({})

    def get_mapped_method(self, request):
        request_method = request.method.upper()
        method_name = self.callmap.get(request_method, request.method)

        if not hasattr(self, method_name):
            return HttpResponseNotAllowed([method for method in self.callmap.keys() if hasattr(self, method)])

        return getattr(self, method_name, None)

    def set_query_params_to_kwargs(self, request, method, keyword_args):
        argsppec = inspect.getargspec(method)
        if not argsppec.defaults:
            return keyword_args

        kwarg_names = argsppec.args[-len(argsppec.defaults):]
        for name in kwarg_names:
            if request.GET.get(name) != None:
                keyword_args[un_camel(name)] = request.GET.get(name)

        return keyword_args

    def insert_into_arglist(self, arglist, item):
        arglist = list(arglist)
        arglist.insert(0, item)
        return tuple(arglist)

    def auth_check(self, request, method):
        if not hasattr(method, '_unauthenticated') and not request.user.is_authenticated():
            response = self.view()
            return response.add_errors('401 -- Unauthorized', status=401).serialize()

    def has_body_param(self, method):
        return hasattr(method, '_body_param_class')

    def uses_entity(self, method):
        return hasattr(method, "_entity_model") and hasattr(method, "_entity_model_arg")

    def has_updates_param(self, method):
        return hasattr(method, "_updates_model") and hasattr(method, "_updates_model_arg")


class EntityNotFoundException(Exception):
    pass
