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

        self.django_model = getattr(dto_class, "_model", None)

        self.payload = {}

        # The dto class refers to a django object, build the base payload
        # for that class given the provided payload
        if self.django_model is not None:
            ret = self.get_allowed_model_payload(payload)
        else:
            # just a `popo` dto, look at the proprties
            # and try and build a payload based on that
            inst = dto_class()
            provided_fields = [f for f in dto_class.__dict__.keys() if not f.startswith("_") and not
                               callable(getattr(inst, f, None))]

            # no properties on the DTO class, must be arbitrary object DTO
            if not provided_fields:
                ret = payload or {}
            else:
                # loop over the fields
                for field in provided_fields:
                    if payload is not None:
                        # use provided payload to populate
                        ret[field] = payload.get(field)
                    else:
                        # use default defined in DTO definition
                        ret[field] = getattr(inst, field, "")

        # finally, apply our ignored and allowed fields filters
        for key, value in ret.iteritems():
            if key in self.ignored_fields:
                continue
            if self.allowed_fields and key not in self.allowed_fields:
                continue
            self.payload[key] = value

        super(Payload, self).__init__(**self.payload)

    def to_obj(self):
        if self.django_model:
            inst = self.django_model()
        else:
            inst = self.dto_class()
            # our dto_class inherhits from dict,
            # user is trying to allow an arbitrary dictionary, just use what we have
            if isinstance(inst, dict):
                return self.payload

        for key, value in self.iteritems():
            setattr(inst, key, value)
        return inst

    def get_allowed_model_payload(self, payload=None):
        """
        Given a dictionary payload, return a dictionary representing
        the values allowed to be set by the underlying model
        (ignoring any _ignores or _hides properties on the dto)

        if no dictionary is passed, returns all the fields (and default values)
        of the given model
        """
        ret = self.create_test_model_payload()

        if payload is not None:
            return {k: v for k, v in payload.iteritems() if k in ret.keys()}

        return ret

    def create_test_payload(self):
        if not self.payload and self.dto_class.__doc__:
            try:
                # no payload, we must be using an empty dto class (no properties)
                # just try and build an example payload from the doc string
                self.payload = json.loads(self.dto_class.__doc__.strip())
            except json.JSONDecodeError:
                self.payload = {}

        return json.dumps(self.payload, indent=4)

    def create_test_model_payload(self):
        """
        Use our django mmodel to construct a test payload, looking at the default values
        for the fields where we can
        """
        ret = {}

        for field in self.django_model._meta.fields:
            field_name = field.attname
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
