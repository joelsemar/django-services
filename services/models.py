from datetime import datetime
from django.conf import settings

if 'gis.db' in settings.DATABASES.get('default', {}).get('ENGINE', ''):
    from django.contrib.gis.db import models
else:
    from django.db import models

class BaseModel(models.Model):
    created_date = models.DateTimeField(default=datetime.utcnow, db_index=True)
    last_modified = models.DateTimeField(default=datetime.utcnow, db_index=True)

    class Meta:
        abstract = True

    @property
    def dict(self):
        ret = self.__dict__
        return dict((k,v) for k,v in ret.items() if not k.startswith('_'))

    def save(self, *args, **kwargs):
        self.last_modified = datetime.utcnow()
        super(BaseModel, self).save(*args, **kwargs)
