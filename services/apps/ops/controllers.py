from services.controller import BaseController
import datetime
import socket
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import send_mail
from services.apps.ops.models import ErrorReport
from services import utils
import logging
logger = logging.getLogger('default')

class StatusController(BaseController):

    def read(self, request, response):
        """
        Server status endpoint
        API Handler: GET /ops/status
        """
        sql_connectivity = True
        sdb_connectivity = True

        try:
            import pycassa
            pycassa.pool.ConnectionPool(settings.DEFAULT_CASSANDRA_KEYSPACE, settings.CASSANDRA_SERVERS)
        except:
            sdb_connectivity = False

        try:
            User.objects.filter(id=1)
        except:
            sql_connectivity = False

        response.set(sdb_connectivity=sdb_connectivity)
        response.set(sql_connectivity=sql_connectivity)
        response.set(timestamp=datetime.datetime.utcnow())
        response.set(hostname=socket.gethostname())

class DeployController(BaseController):
     pass


class HealthController(BaseController):
     internal = True

     def read(self, request, response):
         pass


class ErrorReportController(BaseController):

    def create(self, request, response):
        """
        Report an error or timeout to the server
        API Handler: POST /ops/error

        Params:
          @report [text] Text for WTF happened
          @request_id [text] semi-unique string for identifying the request in the logs
          @when [datetime] timestamp for when the thing happened
        """
        try:
            report = request.POST.get('report')
            request_id = request.POST.get('request_id')
            when = utils.default_time_parse(request.POST.get('when', ''))
            send_mail("Error Report", report, 'ops@canwecode.com', [a[1] for a in settings.ADMINS], fail_silently=True)
            if request.user.is_authenticated():
                profile = request.user.get_profile()
                report += '\n%s %s' % (profile.name, profile.id)
                ErrorReport.objects.create(report=report, request_id=request_id, when=when,
                        profile_id=request.user.get_profile().id)
            else:
                ErrorReport.objects.create(report=report, request_id=request_id, when=when)
        except Exception,  e:
            logger.error(e)


