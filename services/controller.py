
import logging
import json
import inspect
from importlib import import_module
from django.conf import settings
from django.http import HttpResponse, HttpResponseNotAllowed, QueryDict
from django.db.models import Model as DjangoModel
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.fields import DateTimeField, DateField

from services.utils import generic_exception_handler, un_camel_dict, un_camel, default_time_parse
from services.view import BaseView
from services.payload import Payload
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

        request.camel_case = request.META.get(
            "X-SERVICES-CAMEL") is not None or request.GET.get("_camel")
        self.fix_delete_and_put(request)
        self.build_payload(request)

        try:
            mapped_method = self.get_mapped_method(request)
        except NotAllowedException:
            return HttpResponseNotAllowed()

        if not mapped_method:
            return HttpResponse("Not Found", status=404)

        auth_result = self.auth_check(request, mapped_method)

        if auth_result:
            return auth_result

        try:
            if self.has_body_param(mapped_method):
                body_param = self.build_body_param(request, mapped_method)
                if body_param:
                    request.body_param = body_param
                    args = self.insert_into_arglist(args, body_param)

            if self.has_updates_param(mapped_method):
                self.build_updates_param(request, mapped_method, kwargs)

            if self.uses_entity(mapped_method):
                self.set_entity_param(request, mapped_method, kwargs)

            if self.uses_entities(mapped_method):
                self.set_entities_param(request, mapped_method, kwargs)

            kwargs = self.set_query_params_to_kwargs(
                request, mapped_method, kwargs)

        except EntityNotFoundException as e:
            return self.view(request).not_found(str(e)).serialize()

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

        # user has replaced baseview with something else (likely HttpResponse
        # or HttpResponseRedirect), we are done
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
        request.payload = {}

        if request.method == "GET":
            return

        content_type = request.META.get("CONTENT_TYPE", "application/json")
        if content_type == 'application/json':
            try:
                request.payload = json.loads(request.body)
            except Exception as e:
                raise Exception('Invalid JSON data ' + e.message)

        elif "form-urlencoded" in content_type:
            request.payload = getattr(
                request, request.method.upper(), {}).dict()

        if getattr(request, 'camel_case', False) and getattr(request, 'payload', False):
            request.payload = un_camel_dict(request.payload)

    def get_view(self, request, mapped_method):
        # decorators attach the View class to the method itself as '_view',
        # first look there
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
        elif isinstance(method_view, BaseView):
            view = method_view
            view.reset(request)

        else:
            raise Exception(
                "Invalid view argument %s, must extend BaseView" % method_view)

        return view

    def build_body_param(self, request, mapped_method):

        if not getattr(request, 'payload', None):
            return None

        body_param_class = getattr(mapped_method, '_body_param_class', None)

        if not body_param_class:
            return None

        payload = Payload(body_param_class, request.payload)
        return payload.to_obj()

    def build_updates_param(self, request, method, kwargs):
        if not getattr(request, 'payload', None):
            return None

        model_class = getattr(method, "_updates_model")

        updates_model_arg = getattr(method, '_updates_model_arg', None)

        model_instance = self.get_model_instance(
            request, method, model_class, updates_model_arg, kwargs)

        cleaned_payload = Payload(model_class, request.payload)

        self.update_model_instance_with_payload(
            model_instance, cleaned_payload)

        if updates_model_arg:
            kwargs[updates_model_arg] = model_instance

    def update_model_instance_with_payload(self, model_instance, payload):
        if model_instance and payload:
            for field in model_instance._meta.fields:
                if field.primary_key:
                    continue
                if field.attname not in payload.keys() and field.name not in payload.keys():
                    continue
                val = payload.get(field.name, payload.get(field.attname))
                if field.__class__ in (DateTimeField, DateField):
                    val = default_time_parse(val)
                setattr(model_instance, field.attname, val)

    def set_entity_param(self, request, method, kwargs):
        model_class = getattr(method, "_entity_model")

        entity_model_arg = getattr(method, '_entity_model_arg', None)

        model_instance = self.get_model_instance(
            request, method, model_class, entity_model_arg, kwargs)

        if model_instance:
            kwargs[entity_model_arg] = model_instance

    def set_entities_param(self, request, method, kwargs):
        queryset = self.get_queryset(
            request, method, "_queryset_model", "_queryset_model_arg", kwargs)
        if queryset:
            entity_model_arg = getattr(method, '_queryset_model_arg')
            kwargs[entity_model_arg] = queryset

    def get_model_instance(self, request, method, model_class, model_arg, kwargs):
        """
        model_class -> the django model class

        model_arg ->  this is the optional keyword argument used to lookup the model instance
        for example in GET /foo/(?P<foo_id>[\d]) django will provide a kwarg of "foo_id",
        We'll fetch that from the kwargs and try to fetch the model via pk=<foo_id>
        """

        if hasattr(model_class, '_model'):
            model_class = getattr(model_class, '_model')

        try:
            if kwargs.get(model_arg):
                return model_class.objects.get(pk=kwargs[model_arg])
            elif model_arg == "user":
                # no kwarg, maybe trying to operate on current user?
                return request.user
            else:
                # fallback to trying to operate on a single object with one to one with user
                return model_class.objects.get(user=request.user)
        except ObjectDoesNotExist:
            raise EntityNotFoundException(model_arg + " not found.")

    def get_queryset(self, request, method, model_arg_type, arg_type, kwargs):
        if hasattr(method, model_arg_type):
            model_class = getattr(method, model_arg_type)
            if hasattr(model_class, '_model'):
                model_class = getattr(model_class, '_model')
            model_arg = getattr(method, arg_type)
            if kwargs.get(model_arg):
                return model_class.objects.filter(id=kwargs[model_arg])
            else:
                return model_class.objects.filter(user=request.user)

    def fix_delete_and_put(self, request):
        if request.method == "PUT":
            request.PUT = QueryDict(request.body)
            request.request_id = request.PUT.get('request_id')
            request.POST = QueryDict({})

       # if request.method == "DELETE" and request.body:
       #     request.DELETE = QueryDict(request.body)
       #     if not request.DELETE.keys():
       #         request.DELETE = QueryDict(request.META['QUERY_STRING'])
       #         request.POST = QueryDict({})

    def get_mapped_method(self, request):
        request_method = request.method.upper()
        method_name = self.callmap.get(request_method, request.method)

        if not hasattr(self, method_name):
            NotAllowedException()

        return getattr(self, method_name, None)

    def set_query_params_to_kwargs(self, request, method, keyword_args):
        argsppec = inspect.getargspec(method)
        if not argsppec.defaults and not argsppec.keywords:
            return keyword_args

        # method signature has a **kwargs type argument, give them everything
        if argsppec.keywords:
            for key in request.GET.keys():
                if key not in ["page_number", "limit"]:
                    keyword_args[un_camel(key)] = request.GET.get(key)

        # just provide the specifically designated keyword args
        else:
            kwarg_names = argsppec.args[-len(argsppec.defaults):]
            for name in kwarg_names:
                if request.GET.get(name) is not None:
                    keyword_args[un_camel(name)] = request.GET.get(name)

        return keyword_args

    def insert_into_arglist(self, arglist, item):
        arglist = list(arglist)
        arglist.insert(0, item)
        return tuple(arglist)

    def auth_check(self, request, method):
        if not hasattr(method, '_unauthenticated') and not request.user.is_authenticated():
            response = BaseView(request)
            return response.add_errors('401 -- Unauthorized', status=401).serialize()

    def has_body_param(self, method):
        return hasattr(method, '_body_param_class')

    def uses_entity(self, method):
        return hasattr(method, "_entity_model") and hasattr(method, "_entity_model_arg")

    def uses_entities(self, method):
        return hasattr(method, "_queryset_model") and hasattr(method, "_queryset_model_arg")

    def has_updates_param(self, method):
        return hasattr(method, "_updates_model") and hasattr(method, "_updates_model_arg")


class EntityNotFoundException(Exception):
    pass


class NotAllowedException(Exception):
    pass
