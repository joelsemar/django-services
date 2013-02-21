from celery import task
from services.apps.ops.models import EventLog



@task()
def log_api_interaction(**kwargs):

    event = EventLog()
    event.request_id = kwargs.get('request_id')
    event.profile_id = kwargs.get('profile_id')
    event.session_id = kwargs.get('session_id')
    event.host = kwargs.get('host')
    event.path = kwargs.get('path')
    event.request_method =  kwargs.get('request_method')
    event.query_string = kwargs.get('query_string')
    event.request_body = kwargs.get('request_body')
    event.response_body = kwargs.get('response_body')
    event.status_code = str(kwargs.get('status_code', ''))[:4]
    event.when = kwargs.get('when')
    event.save()



