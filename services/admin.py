from django.conf import settings
from django.contrib import admin
from django.db.models.base import ModelBase

for app in settings.INSTALLED_APPS:
    module = __import__(app)
    if not hasattr(module, 'models'):
        continue

    models = getattr(module, 'models')

    for model_name in dir(models):
        m = getattr(models, model_name)
        if isinstance(m, ModelBase) and not m._meta.abstract:
            try:
                admin.site.register(m)
            except admin.sites.AlreadyRegistered:
                pass
