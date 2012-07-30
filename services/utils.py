import datetime
import logging
import re
import simplejson
import sys
import types
import urllib
import urllib2
import xml.sax.handler

from django.db import transaction
from django.contrib.gis.geos import fromstr
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder

from services.view import BaseView as JSONResponse
import requests

GOOGLE_REVERSE_URL = 'http://maps.googleapis.com/maps/api/geocode/json?sensor=false'
GOOGLE_API_URL = "http://maps.google.com/maps/geo?output=json&sensor=false"
GEOIP_URL = "http://api.hostip.info/get_json.php?ip=%s&position=true"

class GeoCodeError(Exception):
    pass

class ReverseGeoCode():

    def __init__(self, latlng):
        self.query = friendly_url_encode({'latlng': latlng})


    def get_address(self):
        response = simplejson.loads(urllib2.urlopen(GOOGLE_REVERSE_URL + '&' + self.query).read())
        ret = response['results']
        if not ret:
            raise GeoCodeError('Invalid coordinates')
        return ret


class GeoCode():

    def __init__(self, address):
        self.query = friendly_url_encode({'q': address})

    def _make_call(self):
        return simplejson.loads(urllib2.urlopen(GOOGLE_API_URL + '&' + self.query).read())

    def get_response(self):
        return  self._make_call()["Placemark"]

    def get_coords(self):
        response = self._make_call()
        coordinates = response['Placemark'][0]['Point']['coordinates'][0:2]
        return tuple([float(n) for n in coordinates])


def friendly_url_encode(data):
    # makes sure that for every item in your data dictionary that is of unicode type, it is first UTF-8
    # encoded before passing it in to urllib.urlencode()
    data = dict([(k, v.encode('utf-8') if type(v) is types.UnicodeType else v) for (k, v) in data.items()])
    return urllib.urlencode(data)


def location_from_coords(lng, lat):
    return fromstr('POINT(%.5f %.5f)' % (float(lng), float(lat)))

def generic_exception_handler(request, exception):
    response = JSONResponse()
    _, _, tb = sys.exc_info()
    # we just want the last frame, (the one the exception was thrown from)
    lastframe = get_traceback_frames(tb)[-1]
    location = "%s in %s, line: %s" % (lastframe['filename'], lastframe['function'], lastframe['lineno'])
    response.add_errors([exception.message, location])
    logger = logging.getLogger('webservice')
    logger.debug([exception.message, location])
    if transaction.is_dirty():
        transaction.rollback()
    return response.send()


def get_traceback_frames(tb):
    """
    Coax the line number, function data out of the traceback we got from the exc_info() call
    """
    frames = []
    while tb is not None:
        # support for __traceback_hide__ which is used by a few libraries
        # to hide internal frames.

        if not tb.tb_frame.f_locals.get('__traceback_hide__'):
            frames.append({
                'filename': tb.tb_frame.f_code.co_filename,
                'function': tb.tb_frame.f_code.co_name,
                'lineno': tb.tb_lineno,
            })
        tb = tb.tb_next

    return frames

def default_time_parse(time_string):
    """
    Expects times in the formats: "2011-12-25 18:22",  "2011-12-25 18:22:12",  "2011-12-25 18:22:12.241512", "2012-02-29"
    Returns None on error
    """
    formats = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d")

    if not time_string or not isinstance(time_string, basestring):
        return None

    for fmt in formats:
        try:
            return datetime.datetime.strptime(time_string, fmt)
        except ValueError:
            pass
    return None

def today():
    """
    Returns a datetime object for today with hour/min zeroed out
    """
    today = datetime.datetime.utcnow()
    return datetime.datetime(today.year, today.month, today.day)

def flatten(items):
    '''Returns the result of flattening non-dictionary iterables
    and scalars down to a single iterable, in a style typical for LISP.
    Parameter must be an iterable.  Type of the returned result is the
    same as items' type.

    This function is non-recursive and relatively fast.

    >>> flatten([1, (2, 3), [(4, 5, 6), 7], set([8, (9, 10)])])
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    >>> flatten(set([1, (2, 3), ((4, 5, 6), 7), (8, (9, 10))]))
    set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    '''
    first_type = type(items)
    items = list(items)
    i = 0
    while i < len(items):
        while hasattr(items[i], '__iter__'):
            if not items[i]:
                items.pop(i)
                i -= 1
                break
            else:
                items[i:i + 1] = items[i]
        i += 1
    return first_type(items)

def str_to_bool(str):
    return str.lower() in ['1', 'true', 't', 'y', 'yes']

def fromXML(src):
    """
    A simple function to converts XML data into native Python object.

    Function taken from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/534109

    XML is a popular mean to encode data to share between systems. Despite its ubiquity, there is no straight forward way to translate XML to Python data structure. Traditional API like DOM and SAX often require undue amount of work to access the simplest piece of data.

    This method convert XML data into a natural Pythonic data structure. For example:

    >>> SAMPLE_XML = \"\"\"<?xml version="1.0" encoding="UTF-8"?>
    ... <address_book>
    ...   <person gender='m'>
    ...     <name>fred</name>
    ...     <phone type='home'>54321</phone>
    ...     <phone type='cell'>12345</phone>
    ...     <note>"A<!-- comment --><![CDATA[ <note>]]>"</note>
    ...   </person>
    ... </address_book>
    ... \"\"\"
    >>> address_book = fromXML(SAMPLE_XML)
    >>> person = address_book.person

    To access its data, you can do the following:

    person.gender        -> 'm'     # an attribute
    person['gender']     -> 'm'     # alternative dictionary syntax
    person.name          -> 'fred'  # shortcut to a text node
    person.phone[0].type -> 'home'  # multiple elements becomes an list
    person.phone[0].data -> '54321' # use .data to get the text value
    str(person.phone[0]) -> '54321' # alternative syntax for the text value
    person[0]            -> person  # if there are only one <person>, it can still
                                    # be used as if it is a list of 1 element.
    'address' in person  -> False   # test for existence of an attr or child
    person.address       -> None    # non-exist element returns None
    bool(person.address) -> False   # has any 'address' data (attr, child or text)
    person.note          -> '"A <note>"'

    This function is inspired by David Mertz' Gnosis objectify utilities. The motivation of writing this recipe in its simplicity. With just 100 lines of code packaged into a single function, it can easily be embedded with other code for ease of distribution.
    """


    if isinstance(src, unicode):
        #try to take it down to a string if necessary. It may generate an error, but it would throw an error
        # anyhow if we tried to run with a unicode string
        src = str(src)

    non_id_char = re.compile('[^_0-9a-zA-Z]')
    def _name_mangle(name):
        return non_id_char.sub('_', name)

    class DataNode(object):
        def __init__(self):
            self._attrs = {}    # XML attributes and child elements
            self.data = None    # child text data
        def __len__(self):
            # treat single element as a list of 1
            return 1
        def __getitem__(self, key):
            if isinstance(key, basestring):
                return self._attrs.get(key, None)
            else:
                return [self][key]
        def __setitem__(self, key, value):
            self._attrs[key] = value
        def __contains__(self, name):
            return self._attrs.has_key(name)
        def __nonzero__(self):
            return bool(self._attrs or self.data)
        def __getattr__(self, name):
            if name.startswith('__'):
                # need to do this for Python special methods???
                raise AttributeError(name)
            return self._attrs.get(name, None)
        def _add_xml_attr(self, name, value):
            if name in self._attrs:
                # multiple attribute of the same name are represented by a list
                children = self._attrs[name]
                if not isinstance(children, list):
                    children = [children]
                    self._attrs[name] = children
                children.append(value)
            else:
                self._attrs[name] = value
        def __str__(self):
            return self.data or ''
        def __unicode__(self):
            return unicode(self.data) or u''
        def __repr__(self):
            items = sorted(self._attrs.items())
            if self.data:
                items.append(('data', self.data))
            return u'{%s}' % ', '.join([u'%s:%s' % (k, repr(v)) for k, v in items])

    class TreeBuilder(xml.sax.handler.ContentHandler):
        def __init__(self):
            self.stack = []
            self.root = DataNode()
            self.current = self.root
            self.text_parts = []
        def startElement(self, name, attrs):
            self.stack.append((self.current, self.text_parts))
            self.current = DataNode()
            self.text_parts = []
            # xml attributes --> python attributes
            for k, v in attrs.items():
                self.current._add_xml_attr(_name_mangle(k), v)
        def endElement(self, name):
            text = ''.join(self.text_parts).strip()
            if text:
                self.current.data = text
            if self.current._attrs:
                obj = self.current
            else:
                # a text only node is simply represented by the string
                obj = text or ''
            self.current, self.text_parts = self.stack.pop()
            self.current._add_xml_attr(_name_mangle(name), obj)
        def characters(self, content):
            self.text_parts.append(content)

    builder = TreeBuilder()
    if isinstance(src, basestring):
        xml.sax.parseString(src, builder)
    else:
        xml.sax.parse(src, builder)
    return builder.root._attrs.values()[0]

def isDirty(model, fieldName):
    """
    Compares a given model instance with the DB and tells you whether or not it has been altered since the last save()
    """
    entryInDB = None
    try:
        entryInDB = model.__class__.objects.get(id=model.id)
    except ObjectDoesNotExist:
        raise Exception("A serious error has occurred in db_utils.isDirty(). A model instance was passed that doesn't exist.")
    return re.sub('[\r\n\ ]+', '', entryInDB.__dict__.get(fieldName, 'none')) != re.sub('[\r\n\ ]+', '', model.__dict__.get(fieldName, 'none'))



class JSONField(models.TextField):
    """JSONField is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly"""

    # Used so to_python() is called
    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        """Convert our string value to JSON after we load it from the DB"""

        if value == "":
            return None

        try:
            if isinstance(value, basestring):
                return simplejson.loads(value)
        except ValueError:
            pass

        return value

    def get_db_prep_save(self, value, connection):
        """Convert our JSON object to a string before we save"""

        if value == "":
            return None

        if isinstance(value, dict):
            value = simplejson.dumps(value, cls=DjangoJSONEncoder)

        return super(JSONField, self).get_db_prep_save(value, connection)

def geo_from_ip(ip):
    geo =  simplejson.loads(urllib2.urlopen(GEOIP_URL % ip).read())
    return geo['lng'], geo['lat']

from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["services.utils.JSONField"])
