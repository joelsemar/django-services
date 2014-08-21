# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'BlogPost'
        db.create_table(u'main_blogpost', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.utcnow, db_index=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.utcnow, db_index=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal(u'main', ['BlogPost'])


    def backwards(self, orm):
        # Deleting model 'BlogPost'
        db.delete_table(u'main_blogpost')


    models = {
        u'main.blogpost': {
            'Meta': {'object_name': 'BlogPost'},
            'created_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.utcnow', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.utcnow', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        }
    }

    complete_apps = ['main']