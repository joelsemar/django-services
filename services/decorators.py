from functools import wraps
from services import utils
from services.view import BaseView
from services.lib.decorator import decorator as _decorator
import datetime


@_decorator
def ranged(decorated_function):
    def new_function(*args, **kwargs):
        for arg in args:
            if hasattr(arg, 'GET'):
                request = arg
        since = utils.default_time_parse(request.GET.get('from_date', '')) or datetime.datetime(1970, 1, 1)
        until = utils.default_time_parse(request.GET.get('to_date', '')) or utils.today()
        args = list(args)
        query = {"date": {'$lte': until, '$gte': since}}
        args.append(query)
        decorated_function(*args, **kwargs)

    if hasattr(decorated_function, '_view'):
        new_function._view = decorated_function._view
    return new_function


def render_with(view):
    return tag_function('_view', view)


# deprecating this guy in favor of  white list, keep it around so as not to cause too much trouble
@_decorator
def login_required(decorated_function):
    return decorated_function


def unauthenticated(decorated_function):
    setattr(decorated_function, '_unauthenticated', True)
    return decorated_function


@_decorator
def superuser_only(decorated_function):
    decorated_function.login_required = True  # for documentation purposes

    @wraps(decorated_function)
    def new_function(*args, **kwargs):
        try:
            request = [a for a in args if hasattr(a, 'user')][0]
        except IndexError:
            response = BaseView()
            return response.add_errors("Login required method called without request object", status=500)

        response = BaseView(request=request)
        if request.user.is_authenticated() and request.user.is_superuser:
            return decorated_function(*args, **kwargs)

        return response.add_errors('401 -- Unauthorized', status=401)

    return new_function


def body(model_class):
    return tag_function('_body_param_class', model_class)


def entity(model_class, arg=''):
    return multitag_function(['_entity_model', '_entity_model_arg'], [model_class, arg])


def updates(model_class, arg=''):
    return multitag_function(['_updates_model', '_updates_model_arg'], [model_class, arg])


def tag_function(tag, item):
    return multitag_function([tag], [item])


def multitag_function(tags, items):
    def decorator(decorated_function):
        for idx, tag in enumerate(tags):
            setattr(decorated_function, tag, items[idx])
        return decorated_function
    return decorator
