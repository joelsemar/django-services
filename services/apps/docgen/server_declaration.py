import re
import os
import importlib
import json
import inspect
from services.controller import BaseController
from services.views import PagingQuerySetView
from django.conf import settings
from django.db.models.fields import NOT_PROVIDED as DEFAULT_NOT_PROVIDED
from django.db.models import Model as DjangoModel
from services.models import BaseModel

# VAR_REGEX = r'^[@][\w]+\ \[[\w\[\]]+\]\ .+' # @parameter [type] some comment
VAR_REGEX = r'^[\s\t\ ]+\@.+'
VAR_SPLIT_REGEX = r'[\s\t\ ]+\@'

RETURN_VAL_REGEX = r'^[\s\t\ ]+\@\@.+'
RETURN_VAL_SPLIT_REGEX = r'[\s\t\ ]+\@\@'


class ServerDeclaration():

    def __init__(self):
        self.handlers = self.crawl_urls()
        self.handler_list = []

        for handler in self.handlers:
            self.handler_list.append({'name': re.sub('Controller$', '', handler.__class__.__name__),
                                      'methods': self.get_methods(handler)})

        self.handler_list.sort(key=lambda x: x['name'])

    def get_methods(self, handler):
        ret = []
        call_map = handler.callmap
        for request_method in call_map.keys():
            if not hasattr(handler, call_map[request_method]):
                continue

            method_name = call_map[request_method]
            method = getattr(handler, method_name)
            docstring = method.__doc__
            if not docstring:
                continue
            auth_required = False
            if not hasattr(method, '_unauthenticated'):
                auth_required = True

            api_handler = self._get_method_api_handler(docstring)

            method_dict = {'name': method_name, 'request_method': request_method,
                           'url': os.path.join(getattr(settings, 'URL_BASE', ''), api_handler.get('url', '/')),
                           'comment': api_handler.get('comment'),
                           'params': self._get_method_params(docstring), 'auth_required': auth_required,
                           'return_vals': self._get_return_vals(docstring), }

            if hasattr(method, '_body_param_class'):
                method_dict['body_param_class'] = getattr(method, '_body_param_class').__name__
                method_dict['test_payload'] = self.create_test_payload(getattr(method, '_body_param_class'))

            if hasattr(method, '_updates_model'):
                method_dict['body_param_class'] = getattr(method, '_updates_model').__name__
                method_dict['test_payload'] = self.create_test_payload(getattr(method, '_updates_model'))

            if hasattr(method, '_view'):
                view = getattr(method, '_view')

                if hasattr(view, 'auto_page') and getattr(view, 'paging', False):
                    method_dict['params'].append({'name': 'page_number', 'type': 'int', 'comment': "Page number"})
                    method_dict['params'].append({'name': 'limit', 'type': 'int', 'comment': "Page Size"})

            ret.append(method_dict)

        return ret

    def _get_method_api_handler(self, docstring):

        api_handler = re.search(r'api handler\:? (?P<method>post|put|get|delete)[\ ](?P<url>.+)', docstring, flags=re.IGNORECASE)
        if api_handler:
            ret = api_handler.groupdict()
            comment = re.search(r'^(?P<comment>.*)api handler', docstring, flags=re.IGNORECASE | re.DOTALL)
            if comment:
                ret['comment'] = comment.groupdict()['comment'].replace('\n', '<br/>')
            return ret
        return {}

    def _get_method_params(self, docstring):
        return self._parse_params(docstring, VAR_REGEX, VAR_SPLIT_REGEX, 0)

    def _get_return_vals(self, docstring):
        if docstring and 'Returns:' in docstring:
            return self._parse_params(docstring, VAR_REGEX, VAR_SPLIT_REGEX, 1)
        return []

    def _parse_params(self, docstring, regex, split_regex, idx):
        ret = []
        if not docstring:
            return ret

        params = re.findall(regex, docstring.split('Returns:')[idx], flags=re.MULTILINE | re.DOTALL)
        if params:
            params = [f.strip() for f in re.split(split_regex, params[0]) if f.strip()]
        for param in params:
            ret.append(self._get_dict_from_var_declaration(param))
        return ret

    def _get_dict_from_var_declaration(self, declaration):
        param = re.search(r'^(?P<name>[\w]+)[\ ]+\[(?P<type>[\w\[\]]+)\][\ ]*(?P<comment>.*)', declaration, flags=re.DOTALL)
        if not param:
            return {}
        param = param.groupdict()
        param['comment'] = re.sub('\n', '<br />', param['comment'])
        if re.search('(optional)', declaration):
            param['comment'] = re.sub('\(optional\)', '', param['comment'])
            param['required'] = '0'
        else:
            param['required'] = '1'
        return param

    def create_test_payload(self, body_param_class):
        ret = {}
        hidden_fields = getattr(body_param_class, '_hides', [])

        if DjangoModel in inspect.getmro(body_param_class):
            for field in body_param_class._meta.fields:
                field_name = field.name
                if field.primary_key:
                    continue

                if field_name in [f.name for f in BaseModel._meta.fields]:
                    continue

                if field_name in hidden_fields:
                    continue

                default = field.default
                if default == DEFAULT_NOT_PROVIDED or default == '':
                    ret[field_name] = ""

                elif not hasattr(field.default, '__call__'):
                    ret[field_name] = field.default

        else:
            for prop in dir(body_param_class):
                if not prop.startswith("_") and prop not in hidden_fields:
                    ret[prop] = getattr(body_param_class, prop)

        return json.dumps(ret, indent=4)

    def crawl_urls(self):
        ret = []
        handler_names = []
        urls = importlib.import_module(settings.ROOT_URLCONF)
        all = []

        def _crawl_urls(urllist):
            for entry in urllist:
                if hasattr(entry, 'url_patterns'):
                    _crawl_urls(entry.url_patterns)
                else:
                    callback = entry.callback
                    all.append(entry)

                    if isinstance(callback, BaseController):
                        handler_name = callback.__class__.__name__
                        if handler_name not in handler_names and not getattr(callback.__class__, 'internal', False):
                            handler_names.append(handler_name)
                            ret.append(callback)

        _crawl_urls(urls.urlpatterns)
        return ret
