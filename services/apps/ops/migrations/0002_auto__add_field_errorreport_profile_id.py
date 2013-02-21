# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'ErrorReport.profile_id'
        db.add_column('ops_errorreport', 'profile_id', self.gf('django.db.models.fields.IntegerField')(null=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'ErrorReport.profile_id'
        db.delete_column('ops_errorreport', 'profile_id')


    models = {
        'ops.errorreport': {
            'Meta': {'object_name': 'ErrorReport'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'profile_id': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'report': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'request_id': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'when': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.utcnow'})
        }
    }

    complete_apps = ['ops']
