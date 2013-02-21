# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'ErrorReport'
        db.create_table('ops_errorreport', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('report', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
            ('request_id', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
            ('when', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.utcnow)),
        ))
        db.send_create_signal('ops', ['ErrorReport'])


    def backwards(self, orm):
        
        # Deleting model 'ErrorReport'
        db.delete_table('ops_errorreport')


    models = {
        'ops.errorreport': {
            'Meta': {'object_name': 'ErrorReport'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'report': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'request_id': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'when': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.utcnow'})
        }
    }

    complete_apps = ['ops']
