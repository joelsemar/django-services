import simplejson as json
from django.db.models.fields import NOT_PROVIDED as DEFAULT_NOT_PROVIDED
from services.models import BaseModel


class Payload(dict):

    def __init__(self, dto_class, payload=None):
        ret = {}
        self.dto_class = dto_class

        # blacklist for input fields
        self.ignored_fields = getattr(dto_class, "_ignores", [])

        # whitelist for input fields
        self.allowed_fields = getattr(dto_class, "_allowed", [])

        self.django_model = getattr(dto_class, "_model")
        if getattr(dto_class, "_hidden_and_ignored", []):
            for field in getattr(dto_class, "_hidden_and_ignored"):
                self.hidden_fields.append(field)
                self.ignored_fields.append(field)

        self.payload = {}
        if self.django_model is not None:
            ret = self.get_allowed_model_payload(payload)
        else:
            inst = dto_class()
            provided_fields = [f for f in dir(inst) if not f.startswith("_") and not callable(f)]
            for field in provided_fields:
                ret[field] = payload.get(field)

        for key, value in ret.iteritems():
            if key in self.ignored_fields:
                continue
            if self.allowed_fields and key not in self.allowed_fields:
                continue
            print "setting %s: %s" % (key, value)
            self.payload[key] = value

        super(Payload, self).__init__(**self.payload)

    def to_obj(self):
        if self.django_model:
            inst = self.django_model()
        else:
            inst = self.dto_class()
        for key, value in self.iteritems():
            setattr(inst, key, value)
        return inst

    def get_allowed_model_payload(self, payload=None):
        """
        Given a dictionary payload, return a dictionary representing
        the Set of values allowed to be set by the underlying model
        (ignoring any _ignores or _hides properties on the dto)

        if no dictionary is passed, returns all the fields (and default values)
        of the given model
        """

        ret = self.create_test_model_payload()

        if payload is not None:
            return {k: v for k, v in payload.iteritems() if k in ret.keys()}

        return ret

    def create_test_payload(self):
        return json.dumps(self.payload, indent=4)

    def create_test_model_payload(self):
        ret = {}

        for field in self.django_model._meta.fields:
            field_name = field.name
            if field.primary_key:
                continue
            if field_name in [f.name for f in BaseModel._meta.fields]:
                continue
            default = field.default
            if default == DEFAULT_NOT_PROVIDED or default == '':
                ret[field_name] = ""

            elif not hasattr(field.default, '__call__'):
                ret[field_name] = field.default

        return ret
