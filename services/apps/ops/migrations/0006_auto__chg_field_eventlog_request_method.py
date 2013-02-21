# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'EventLog.request_method'
        db.alter_column('ops_eventlog', 'request_method', self.gf('django.db.models.fields.CharField')(max_length=8))


    def backwards(self, orm):
        
        # Changing field 'EventLog.request_method'
        db.alter_column('ops_eventlog', 'request_method', self.gf('django.db.models.fields.CharField')(max_length=4))


    models = {
        'ops.errorreport': {
            'Meta': {'object_name': 'ErrorReport'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'profile_id': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'report': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'request_id': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'when': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.utcnow'})
        },
        'ops.eventlog': {
            'Meta': {'object_name': 'EventLog'},
            'host': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'profile_id': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'query_string': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'request_body': ('django.db.models.fields.CharField', [], {'max_length': '1000000'}),
            'request_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '256', 'blank': 'True'}),
            'request_method': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'response_body': ('django.db.models.fields.CharField', [], {'max_length': '1000000'}),
            'session_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'status_code': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'when': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.utcnow'})
        }
    }

    complete_apps = ['ops']
