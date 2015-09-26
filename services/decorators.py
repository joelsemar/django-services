from functools import wraps
from services import utils
from services.view import BaseView
import datetime


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
    def decorator(decorated_function):
        @wraps(decorated_function)
        def new_function(*args, **kwargs):
            return decorated_function(*args, **kwargs)
        new_function._view = view
        return new_function
    return decorator


def login_required(decorated_function):
    decorated_function.login_required = True  # for documentation purposes

    @wraps(decorated_function)
    def new_function(*args, **kwargs):
        try:
            request = [a for a in args if hasattr(a, 'user')][0]
        except IndexError:
            response = [a for a in args if isinstance(a, BaseView)][0]
            response.add_errors("Login required method called without request object", status=500)
            return response
        response = BaseView(request=request)
        if request.user.is_authenticated():
            return decorated_function(*args, **kwargs)

        response.add_errors('401 -- Unauthorized', status=401)
        return response

    return new_function


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


