import datetime
import logging
import re
import simplejson
import sys
import types
import urllib
import urllib2
import xml.sax.handler
import math
from decimal import Decimal

from django.db import transaction
try:
    from django.contrib.gis.geos import fromstr
except:
    pass
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import render

import requests

GOOGLE_GEOCODING_URL = "http://maps.googleapis.com/maps/api/geocode/json?sensor=false"
GEOIP_URL = "http://api.hostip.info/get_json.php?ip=%s&position=true"


class GeoCodeError(Exception):
    pass


class ReverseGeoCode():

    def __init__(self, lng, lat):
        latlng = '%s,%s' % (lat, lng)
        self.query = friendly_url_encode({'latlng': latlng})

    def get_address(self):
        response = simplejson.loads(urllib2.urlopen(GOOGLE_GEOCODING_URL + '&' + self.query).read())
        ret = response['results']
        if not ret:
            raise GeoCodeError('Invalid coordinates')
        return ret


class GeoCode():

    def __init__(self, address):
        self.query = friendly_url_encode({'address': address})

    def get_coords(self):
        response = simplejson.loads(requests.get(GOOGLE_GEOCODING_URL + '&' + self.query).content)
        try:
            lat = response['results'][0]['geometry']['location']['lat']
            lng = response['results'][0]['geometry']['location']['lng']
        except:
            raise GeoCodeError
        return lng, lat


class PlacesClient():
    BASE_URL = "https://maps.googleapis.com/maps/api/place"
    AUTOCOMPLETE = "autocomplete"
    SEARCH = "nearbysearch"
    DETAILS = "details"

    def __init__(self, api_key):
        self.api_key = api_key

    def call(self, url, **kwargs):
        kwargs['key'] = self.api_key
        return requests.get(url, kwargs).json()

    def get_place(self, place_id):
        url = self.url(self.DETAILS)
        return self.call(url, placeid=place_id)

    def autocomplete(self, input, lat=None, lng=None, radius=50000):
        location = "%s,%s" % (lat, lng)
        url = self.url(self.AUTOCOMPLETE)
        return self.call(url, location=location, input=input, radius=radius)

    def search(self, input, lat=None, lng=None, radius=50000):
        location = "%s,%s" % (lat, lng)
        url = self.url(self.SEARCH)
        return self.call(url, location=location, name=input, radius=radius)

    def url(self, path):
        return "{0}/{1}/json".format(self.BASE_URL, path)


def friendly_url_encode(data):
    # makes sure that for every item in your data dictionary that is of unicode type, it is first UTF-8
    # encoded before passing it in to urllib.urlencode()
    data = dict([(k, v.encode('utf-8') if type(v) is types.UnicodeType else v) for (k, v) in data.items()])
    return urllib.urlencode(data)


def location_from_coords(lng, lat):
    return fromstr('POINT(%.5f %.5f)' % (float(lng), float(lat)))


def str_from_location(location):
    """
    Produces a string suitable to be passed into contrib.geos.gis.fromstr
    """
    return 'POINT(%.5f %.5f)' % (float(location.x), float(location.y))


def generic_exception_handler(request, exception):
    from services.view import BaseView
    response = BaseView(request=request)
    _, _, tb = sys.exc_info()
    import traceback
    frames = traceback.extract_tb(tb)
    frame_template = "File %s, line %s, in %s\n  %s\n"
    error_header = '----%s----\n' % datetime.datetime.utcnow()
    error = ''

    for frame in frames:
        error += frame_template % frame

    if len(str(exception.message)) < 2000:
        error += str(exception.message)

    error += '\n'

    response.add_errors(error)
    logger = logging.getLogger('default')
    logger.error(error_header + error)
    try:
        transaction.rollback()
    except Exception as e:
        print "Error rolling back: " + e.message

    return response.serialize()


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
    formats = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S.%f",
               "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ")

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
    if str is None:
        return False
    return str.lower() in ['1', 'true', 't', 'y', 'yes']


def isDirty(model, field_name):
    """)
    Compares a given model instance with the DB and tells you whether or not it has been altered since the last save()
    """
    db_entry = None
    try:
        db_entry = model.__class__.objects.get(id=model.id)
    except ObjectDoesNotExist:
        raise Exception(
            "A serious error has occurred in db_utils.isDirty(). A model instance was passed that doesn't exist.")

    db_data = str(db_entry.__dict__.get(field_name, ''))
    model_data = str(model.__dict__.get(field_name, ''))
    return re.sub('[\r\n\ ]+', '', db_data) != re.sub('[\r\n\ ]+', '', model_data)


def geo_from_ip(ip):
    geo = simplejson.loads(urllib2.urlopen(GEOIP_URL % ip).read())
    return geo['lng'], geo['lat']


def get_one_if(seq, func):
    ret = [i for i in seq if func(i)]
    if ret:
        return ret[0]
    return None


def get_first(seq):
    if seq:
        return seq[0]
    return None


def if_one(seq):
    if seq and len(seq) == 1:
        return seq[0]

    return seq


class DefaultJSONEncoder(simplejson.JSONEncoder):

    def default(self, o):
        try:
            return str(o)
        except:
            return super(DefaultJSONEncoder, self).default(o)


class DateTimeAwareJSONEncoder(DefaultJSONEncoder):

    """
    JSONEncoder subclass that knows how to encode date/time types
    """

    DATE_FORMAT = "%Y-%m-%d"
    TIME_FORMAT = "%H:%M:%S.%f"

    def default(self, o):
        if isinstance(o, datetime.datetime):
            o = datetime.datetime(o.year, o.month, o.day, o.hour, o.minute, o.second, o.microsecond)
            r = o.strftime(self.DATE_FORMAT + 'T' + self.TIME_FORMAT)
            return r[:-3]
        elif isinstance(o, datetime.date):
            return o.strftime(self.DATE_FORMAT)
        elif isinstance(o, datetime.time):
            return o.strftime(self.TIME_FORMAT)
        else:
            return super(DateTimeAwareJSONEncoder, self).default(o)


def flat_earth_distance(lng1, lat1, lng2, lat2):
    # calculate distance, ignoring curvature of the earth
    # based on 'Equirectangular approximation' described here: http://www.movable-type.co.uk/scripts/latlong.html'
    earth_radius = 6371000  # in meters
    p1 = (lng2 - lng1) * math.cos(0.5 * (lat1 + lat2))
    p2 = (lat2 - lat1)
    return earth_radius * math.sqrt(p1 * p1 + p2 * p2)


def direct_to_template(template, context={}):
    return lambda request: render(request, template, context)


first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


def camel(value):
    def camelcase():
        yield str.lower
        while True:
            yield str.capitalize

    c = camelcase()
    return "".join(c.next()(x) if x else '_' for x in value.split("_"))


def camel_dict(dictionary):
    ret = {}
    for k, v in dictionary.items():
        ret[camel(k)] = v

    return ret


def un_camel(string):
    s1 = first_cap_re.sub(r'\1_\2', string)
    return all_cap_re.sub(r'\1_\2', s1).lower()


def un_camel_dict(dictionary):
    ret = {}
    for key, value in dictionary.items():
        ret[un_camel(key)] = value
    return ret
