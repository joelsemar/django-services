from django.core import serializers
import simplejson
import logging
from django.http import HttpResponse

from django.conf import settings
from django.core.paginator import EmptyPage, Paginator
from services.utils import camel_dict

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
        _set = super(BaseView, self).__setattr__
        _set('_errors', [])
        _set('_request', request)
        _set('success', True)
        _set('_data',  {})
        _set('_status', 200)
        _set('headers', {})

    def set_headers(self, headers):
        for k, v in headers.items():
            self.headers[k] = v

    def add_errors(self, errors, status=400):

        self.success = False

        if status:
            self._status = status

        if isinstance(errors, basestring):
            # just a single error
            self._errors.append(errors)
            return self

        elif isinstance(errors, list):
            # a list of errors
            for error in errors:
                self._errors.append(error)
            return self
        raise TypeError("Argument 'errors' must be of type 'string' or 'list'")

    def add_messages(self, messages):
        if isinstance(messages, basestring):
            # just a single message
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
        return self

    def __setattr__(self, key, value):
        if not hasattr(self, key):
            self._data[key] = value
        else:
            super(BaseView, self).__setattr__(key, value)

    def __getattr__(self, key):
        return self.data.get(key)

    def set_status(self, status):
        assert isinstance(status, int)
        self._status = status
        return self

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

    def not_found(self, message="Not Found"):
        return self.add_errors(message, status=404)

    def forbidden(self, message="Forbidden"):
        return self.add_errors(message, status=403)

    def created(self):
        return self.set_status(201)

    def no_content(self):
        return self.set_status(204)

    def should_render(self, request):
        return True

    def _render(self, request):
        if(self.should_render(request)):
            return self.render(request)

        return self._data

    @property
    def pretty_print(self):
        if settings.DEBUG:
            return True

        if hasattr(self, '_request'):
            return self._request.REQUEST.get('pretty_print', False)

        return False

    @property
    def camel_case(self):
        if hasattr(self, '_request'):
            return getattr(self._request, 'camel_case', False)
        return False

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
            response_dict['data'] = self._render(self._request)
            response_dict['errors'] = self._errors
            response_dict['success'] = self.success

        else:
            if self._errors:
                response_dict = {'errors': self._errors}
            else:
                response_dict = self._render(self._request)

        if self.camel_case:
            response_dict = camel_dict(response_dict)

        if self.pretty_print:
            response_body = simplejson.dumps(response_dict, cls=DateTimeAwareJSONEncoder, indent=JSON_INDENT)
        else:
            response_body = simplejson.dumps(response_dict, cls=DateTimeAwareJSONEncoder)

        if response_body == '{}':
            response_body = ''

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

    def should_render(self, request):
        return self.instance

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

    def should_render(self, request):
        return self.queryset

    def __init__(self, request=None, model_view=None, paging=False):
        self.model_view = model_view or self.model_view
        self.paging = paging or self.paging
        super(QuerySetView, self).__init__(request=request)

    @property
    def queryset(self):
        return self._data.get('queryset', None)

    def render(self, request):
        queryset = self.queryset

        if self.paging:
            return self.render_paged(request, queryset)

        ret = [self.model_view.render_instance(obj, request) for obj in queryset]
        ret = self.sort(ret, request)

        return {self.queryset_label: ret}

    def render_paged(self, request, queryset):
        results, paging_dict = self.auto_page(
            queryset, page_number=request.GET.get('page_number', 0), limit=request.GET.get('limit', 20))

        ret = [self.model_view.render_instance(obj, request) for obj in results]
        ret = self.sort(ret, request)

        return {self.queryset_label: ret, 'paging': paging_dict}

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

        total_count = len(results)
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
                     'total_count': total_count,
                     'total_pages': pages.num_pages}

        return results, page_dict


class PagingQuerySetView(QuerySetView):
    paging = True
