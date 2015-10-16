import inspect
from django.db.models import Model as DjangoModel


class Payload(object):

    @classmethod
    def build(cls, payload):
        if DjangoModel in inspect.getmro(cls):
            return Payload.build_django_model_payload(payload)

        inst = cls()
        hidden_fields = getattr(cls, '_hides', [])

        provided_fields = [f for f in dir(inst) if not f.startswith("_") and not callable(f)]

        # just using a basic Payload object, no properties defined
        if not provided_fields:
            for key, value in payload.items():
                setattr(inst, key, value)

        # here we have properties defined, we just grab those
        else:
            for field in provided_fields:
                if payload.get(field) and field not in hidden_fields:
                    setattr(inst, field, payload.get(field))

        return inst

    @classmethod
    def build_django_model_payload(cls, payload):
        inst = cls()
        hidden_fields = getattr(cls, '_hides', [])

        for field in cls._meta.fields:
            # in some cases these are not the same (eg ForeignKey fields)
            # so the client can send us "related_model_name" and we will set the attribute "related_model_name_id"
            field_attname = field.attname
            field_name = field.name

            if field.primary_key:
                continue

            if payload.get(field_name) != None and field_name not in hidden_fields:
                setattr(inst, field_attname, payload.get(field_name))

        return inst
