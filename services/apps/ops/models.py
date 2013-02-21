from django.db import models
import datetime

class ErrorReport(models.Model):
    report = models.TextField(blank=True, default='')
    request_id = models.TextField(blank=True, default='')
    profile_id = models.IntegerField(null=True)
    when = models.DateTimeField(default=datetime.datetime.utcnow)


    def __unicode__(self):
        return unicode(self.report)

class EventLog(models.Model):
    request_id = models.CharField(max_length=256, blank=True, default='')
    profile_id = models.IntegerField(null=True)
    session_id = models.CharField(max_length=128)
    host = models.CharField(max_length=128)
    path = models.CharField(max_length=256)
    request_method = models.CharField(max_length=8)
    query_string = models.CharField(max_length=256)
    request_body = models.CharField(max_length=1000000)
    response_body = models.CharField(max_length=1000000)
    status_code = models.CharField(max_length=3)
    when = models.DateTimeField(default=datetime.datetime.utcnow)

    def __unicode__(self):
       ret = "%s %s" % (self.request_method, self.path)
       if self.query_string:
           ret += '?' + self.query_string
       ret += ' at ' + str(self.when)
       return ret



