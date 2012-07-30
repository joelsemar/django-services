
from bson.objectid import ObjectId    
from datetime import datetime
from services.utils import default_time_parse

class DataField(object):

    def __init__(self, required=True, default=None):
        self.required = required
        super(DataField, self).__setattr__('_value', None)
        self.default = default

    def __setattr__(self, field_name, value):
        
        if field_name == '_value':
            value = self.validate_type(value)
        return super(DataField, self).__setattr__(field_name, value)

    def validate_type(self, value):
        return value


class DataViewField(DataField):

    def __init__(self, data_view):
        self.data_view = data_view

    def __setattr__(self, field_name, data):
        if field_name == '_value':
            data = self.data_view(**data)
        return super(DataViewField, self).__setattr__(field_name, data)


class TextDataField(DataField):

    def validate_type(self, value):
        if not isinstance(value, basestring):
            raise TypeError("TextDataField '%s' must be of type 'basestring'" % self._name)
        return value


class FloatDataField(DataField):

    def validate_type(self, value):
        try:
            value = float(value)
        except ValueError:
            raise TypeError("FloatDataField '%s' must be of type 'float'" % self._name)
        return value

class IntegerDataField(DataField):

    def validate_type(self, value):
        if not isinstance(value, int):
            raise TypeError("IntegerDataField '%s' must be of type 'int'" % self._name)
        return value

class BooleanDataField(DataField):

    def validate_type(self, value):
        
        if not isinstance(value, bool):
            raise TypeError("BooleanDataField '%s' must be of type 'bool'" % self._name)
        return value

class DateTimeDataField(DataField):

    def validate_type(self, value):
        if isinstance(value, basestring):
            value = default_time_parse(value)
        if not isinstance(value, datetime):
            raise TypeError("DateTimeDataField '%s' must be of type 'datetime'" % self._name)
        return value

class ObjectIDDataField(DataField):

    def validate_type(self, value):
        if not isinstance(value, ObjectId):
            raise TypeError("ObjectIDDataField '%s' must be of type 'bson.objectid.ObjectId'" % self._name)
        return value
