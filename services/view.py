from django.core import serializers
import simplejson
import logging
from django.http import HttpResponse

from django.conf import settings
from django.core.paginator import EmptyPage, Paginator

JSON_INDENT = 4

JSONSerializer = serializers.get_serializer('json')

logger = logging.getLogger('default')
legacy_format = getattr(settings, 'API_RESPONSE_LEGACY_FORMAT', True)

class BaseView(object):
    """
    A generic response object for generating and returning api responses
    """
    def __init__(self, request=None):
        self.reset(request)

    def reset(self, request):
        self._errors = []
        self._request = request
        self._messages = []
        self.success = True
        self._data = {}
        self._status = 200
        self.doc = None
        self.headers = {}


    def set_headers(self, headers):
        for k, v in headers.items():
            self.headers[k] = v

    def add_errors(self, errors, status=400):

        self.success = False

        if status:
            self._status = status

        if isinstance(errors, basestring):
            #just a single error
            self._errors.append(errors)
            return

        elif isinstance(errors, list):
            # a list of errors
            for error in errors:
                self._errors.append(error)
            return
        raise TypeError("Argument 'errors' must be of type 'string' or 'list'")

    def add_messages(self, messages):
        if isinstance(messages, basestring):
            #just a single message
            self._messages.append(messages)
            return

        elif isinstance(messages, (list, tuple)):
            # a list of errors
            for message in messages:
                self._messages.append(message)
            return
        self._messages.append(messages)


    def set(self, **kwargs):
        self._data.update(kwargs)

    def __setitem__(self, key, value):
        self._data[key] = value

    def __getitem__(self, key):
        return self._data[key]

    def get(self, key):
        return self._data[key]

    def set_status(self, status):
        assert isinstance(status, int)
        self._status = status

    def render(self, request):
        return self._data

    def render_summary(self, request):
        ret = {'session_key': request.session.session_key,
               'path': request.get_full_path(),
               'method': request.method,
               'body': request.raw_post_body}

        if request.user.is_authenticated():
            ret['user_id'] = request.user.get_profile().id

        ret['body_summary'] = self.get_body_summary(request)

        return ret

    def access_denied(self, message="Access Denied"):
        return self.add_errors(message, status=401)

    def bad_request(self, message="Bad Request"):
        return self.add_errors(message, status=400)

    def not_found(self):
        return self.add_errors("Not Found", status=404)

    def created(self):
        return self.set_status(201)

    def serialize(self, messages=None, errors=None, status=None):
        from services.utils import DateTimeAwareJSONEncoder

        if errors:
            self.add_errors(errors)

        if status:
            self.set_status(status)

        if messages:
            self.add_messages(messages)

        if legacy_format:
            response_dict = {}
            response_dict['data'] = self.render(self._request)
            response_dict['errors'] = self._errors
            response_dict['success'] = self.success

        else:
            if self._errors:
                response_dict = {'errors': self.errors}
            else:
                response_dict =  self.render(self._request)



        if settings.DEBUG or self._request.REQUEST.get('pretty_print'):
            response_body = simplejson.dumps(response_dict, cls=DateTimeAwareJSONEncoder, indent=JSON_INDENT)
        else:
            response_body = simplejson.dumps(response_dict, cls=DateTimeAwareJSONEncoder)
        http_response = HttpResponse(response_body, status=self._status)
        http_response['Content-Type'] = 'application/json'
        return http_response

class ListView(BaseView):

    def dict(self, instance):
        return instance.dict

    def render(self, request):
        ret = {}
        for key, value in self._data.items():
            if isinstance(value, (list, tuple)):
                ret[key] = [self.dict(d) for d in value]
        return ret

class ModelView(BaseView):

    excluded = ()
    fields = ()
    extra_fields = ()

    def render(self, request):

        ret = {}
        if not self.instance:
            return self._data

        if self.fields:
            for field in self.fields:
                ret[field] = getattr(self.instance, field)

        else:
            if hasattr(self.instance, 'dict'):
                return self.instance.dict

            for key, value in self.instance.__dict__.items():
                if not key.startswith('_'):
                    ret[key] = value

            for field in self.excluded:
                del ret[field]

            for field in self.extra_fields:
                ret[field] = getattr(self.instance, field)

        return ret

    @property
    def instance(self):
        return self._data.get('instance', None)

    @classmethod
    def render_instance(cls, instance, request):
        """A Helper method so QuerySet Views can make use of the instance's ModelView"""
        view = cls(request=request)
        view.set(instance=instance)
        return view.render(request)


class QuerySetView(BaseView):
    model_view = ModelView
    paging = False
    queryset_label = 'results'

    def __init__(self, request=None, model_view=ModelView):
        self.model_view = model_view
        super(QuerySetView, self).__init__(request=request)

    @property
    def queryset(self):
        return self._data.get('queryset', None)


    def render(self, request):
        queryset = self.queryset
        if queryset is None:
            return self._data

        ret = []
        for profile in queryset:
            ret.append(self.model_view.render_instance(profile, request))

        ret = self.sort(ret, request)

        if self.paging:
            results, paging_dict = self.auto_page(ret, page_number=request.GET.get('page_number', 1), limit=request.GET.get('limit', 20))
            return {self.queryset_label: results, 'paging': paging_dict}

        return {self.queryset_label: ret}

    @classmethod
    def inline_render(cls, queryset, request):
        """
        A Helper method to render a queryset inline manually
        """
        view = cls()
        view.set(queryset=queryset)
        return view.render(request)['results']

    def sort(self, results, request):
        return results

    def auto_page(self, results, page_number=1, limit=10):

        try:
            page_number = int(page_number)
            limit = int(limit)
        except ValueError:
            page_number = 1
            limit = 10

        pages = Paginator(results, limit)
        try:
            page = pages.page(page_number)
        except EmptyPage:
            page = pages.page(1)

        results = page.object_list

        try:
            pages.page(page.next_page_number())
            next_page = page.next_page_number()
        except EmptyPage:
            next_page = None

        try:
            pages.page(page.previous_page_number())
            previous_page = page.previous_page_number()
        except EmptyPage:
            previous_page = None

        page_dict = {'page': page_number,
                    'next_page': next_page,
                    'previous_page': previous_page,
                    'total_pages': pages.num_pages}

        return results, page_dict

