# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'EventLog'
        db.create_table('ops_eventlog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('request_id', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
            ('profile_id', self.gf('django.db.models.fields.IntegerField')(null=True)),
            ('session_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('host', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('path', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('request_method', self.gf('django.db.models.fields.CharField')(max_length=4)),
            ('query_string', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('request_body', self.gf('django.db.models.fields.TextField')()),
            ('response_body', self.gf('django.db.models.fields.TextField')()),
            ('when', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.utcnow)),
        ))
        db.send_create_signal('ops', ['EventLog'])


    def backwards(self, orm):
        
        # Deleting model 'EventLog'
        db.delete_table('ops_eventlog')


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
            'request_body': ('django.db.models.fields.TextField', [], {}),
            'request_id': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'request_method': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'response_body': ('django.db.models.fields.TextField', [], {}),
            'session_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'when': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.utcnow'})
        }
    }

    complete_apps = ['ops']
