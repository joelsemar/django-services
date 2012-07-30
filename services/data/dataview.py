import re
from pymongo import Connection
from services.data.fields import *

connection = Connection('localhost', 27017)
db = connection.tdeserver

class DataViewException(Exception):
    pass


class DataViewManager(object):

    def __init__(self, collection):
        self.collection = collection

    def get(self, **kwargs):
        return self._init_from_dict(db[self.collection].find_one(kwargs))

    def filter(self, **kwargs):
        return [self._init_from_dict(d) for d in db[self.collection].find(kwargs)] 

    def raw_filter(self, query):
        ##sometimes we need to pass straight to mongo 
        return [self._init_from_dict(d) for d in db[self.collection].find(query)] 


    def create(self, **kwargs):
        ret = self._cls(**kwargs)
        ret.save()
        return ret;

    def _init_from_dict(self, data):
        if not data:
            return None
        return self._cls(**data)



class BaseDataView(type):
    
    def __new__(cls, name, bases, attrs):
        data_view = super(BaseDataView, cls).__new__(cls, name, bases, attrs)
        data_view.collection_name = name.replace('DataView', '').lower()
        data_view.objects = DataViewManager(data_view.collection_name) 
        data_view.objects._cls = data_view
        for field_name, field in attrs.items():
            if isinstance(field, DataField):
                field._name = field_name
            
        return data_view
        

class DataView(object):
    validation_method_regex = r'^check_(?P<field>[\w]+)$'

    __metaclass__ = BaseDataView

    def __init__(self, **args):
        self._data = {}
        for key, value in args.items():
            setattr(self, key, value)

    def __unicode__(self):
        return self._data.__unicode__()
    
    def __setattr__(self, name, value):
        if hasattr(self, '_data'):
            self._data[name] = value

        data_field = self.get_field(name)
        if data_field:
            data_field._value = value
            return
        else:
            try:
               super(DataView, self).__setattr__(name, value)
            except AttributeError:
               print name, value

    def __getattribute__(self, name):
        field = super(DataView, self).__getattribute__(name)
        if isinstance(field, DataField):
            return self._data.get(name)
        return field

    def get_field(self, name):
        try:
            field = super(DataView, self).__getattribute__(name)
        except AttributeError:
            return None

        if not isinstance(field, DataField):
            return None
        return field

    
    @property
    def _fields(self):
        return [self.get_field(f) for f in dir(self) if not f.startswith('_') and self.get_field(f)]

    def save(self):

        if not self.collection_name:
            raise DataViewException("Collection name required")
        if self.validate():
           if not hasattr(self, '_id'): 
               self._id = db[self.collection_name].insert(self._data)
           else:
               db[self.collection_name].update({'_id': self._id}, self._data)

    def validate(self):

        for field in self._fields:
            if self._data.get(field._name) is None:
                if field.default is not None:
                    default = callable(field.default) and field.default() or field.default
                    setattr(self, field._name, default)
                if field.required and self._data.get(field._name) is None: #check again because default could have been set one line up
                    raise DataViewException("%s is required" % field._name)
        
        for name in dir(self):
            match = re.match(self.validation_method_regex, name)
            if match:
                field_name = match.groupdict()['field']
                current_value = getattr(self, field_name)

                if current_value is not None:
                   validated_value = getattr(self, name)(current_value)

                setattr(self, field_name, validated_value)
        return True

    def delete(self):
        db[self.collection_name].remove({'_id': self._id})

    @classmethod
    def map_reduce(cls, *args, **kwargs):
        return db[cls.collection_name].map_reduce(*args, **kwargs);

    
    @property
    def dict(self):
        ret = {}
        for key in self._data:
            if not key.startswith('_'):
                ret[key] = self._data[key]

        return ret
    

class PostDataView(DataView):

    name = TextDataField(required=True)
    foo = FloatDataField(required=True)
    bar = IntegerDataField()

    def check_name(self, name):
        return name.title()
