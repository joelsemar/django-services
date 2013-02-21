from datetime import datetime
from django.db import models
from services import encryption
from services.utils import isDirty



class StoredCredential(models.Model):
    name = models.CharField(max_length=256, db_index=True)
    value = models.TextField(default='', help_text="This field is encrypted")
    last_modified = models.DateTimeField(default=datetime.utcnow)
    created_date = models.DateTimeField(default=datetime.utcnow)

    def __unicode__(self):
        return self.name


    def save(self, *args, **kwargs):
        self.last_modified = datetime.utcnow()

        if not self.id:
            self.value = encryption.encryptData(self.value)
        else:
            if isDirty(self, 'value'):
                self.value = encryption.encryptData(self.value)

        super(StoredCredential, self).save(*args, **kwargs)

    def get_value(self):
        return encryption.decryptData(self.value)
