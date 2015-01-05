"""
Markers and core functions for dates, times, and datetimes.

All three types assume you're using the date, time, and datetime types from the
datetime module.

This module exposes three Markers: DateTime, Date, and Time

validate accepts only datetime, date, or time objects, respectively:

>>> now = datetime.datetime.now()
>>> validate(DateTime(), now)
>>> validate(DateTime(), "")
Traceback (most recent call last):
...
Invalid: type_error

>>> validate(Date(), now.date())
>>> validate(Date(), now.time())
Traceback (most recent call last):
...
Invalid: type_error

>>> validate(Time(), now.time())
>>> validate(Time(), now)
Traceback (most recent call last):
...
Invalid: type_error


Their dictify implementations use ISO 8601 format:

>>> d = datetime.datetime(1776, 12, 25, 14, 21, 3, 100500)
>>> dictify(DateTime(), d)
u'1776-12-25T14:21:03.100500'
>>> dictify(Date(), d.date())
u'1776-12-25'
>>> dictify(Time(), d.time())
u'14:21:03.100500'
>>> dictify(DateTime(), d.replace(microsecond=0))
u'1776-12-25T14:21:03'


>>> undictify(DateTime(), u'1776-12-25T14:21:03.100500')
datetime.datetime(1776, 12, 25, 14, 21, 3, 100500)
>>> undictify(Date(), u'1776-12-25')
datetime.date(1776, 12, 25)
>>> undictify(Time(), u'14:21:03.100500')
datetime.time(14, 21, 3, 100500)
>>> undictify(DateTime(), u'1776-12-25T14:21:03')
datetime.datetime(1776, 12, 25, 14, 21, 3)

Unparseable strings get "bad_format" errors; non-strings get "type_error":

>>> undictify(DateTime(), "20003-1-1")
Traceback (most recent call last):
...
Invalid: bad_format
>>> undictify(DateTime(), "1776-13-25")
Traceback (most recent call last):
...
Invalid: bad_format
>>> undictify(DateTime(), "1776-12-32")
Traceback (most recent call last):
...
Invalid: bad_format
>>> undictify(DateTime(), "1776-12-25T26:25:03.1")
Traceback (most recent call last):
...
Invalid: bad_format
>>> undictify(DateTime(), "1776-12-25T14:71:03.1")
Traceback (most recent call last):
...
Invalid: bad_format
>>> undictify(DateTime(), "1776-12-25T14:25:93.1")
Traceback (most recent call last):
...
Invalid: bad_format
>>> undictify(Date(), "1776-hello-12")
Traceback (most recent call last):
...
Invalid: bad_format
>>> undictify(Time(), "Not even remotely a datetime.")
Traceback (most recent call last):
...
Invalid: bad_format
>>> undictify(DateTime(), ["this", "isn't", "even", "a", "string"])
Traceback (most recent call last):
...
Invalid: type_error



Like all good undictify implementations, it is idempotent:

>>> dt = undictify(DateTime(), "1776-12-25T14:21:03.100500")
>>> undictify(DateTime(), dt) == dt
True
>>> undictify(Date(), dt.date()) == dt.date()
True
>>> undictify(Time(), dt.time()) == dt.time()
True
"""



import datetime

import sys
if sys.version >= '3': # pragma: no cover
    unicode = str
    basestring = str

from .base import Leaf, validate, dictify, undictify
from .invalid import Invalid

class _DateTimeMarker(Leaf):
    _dt_type = None
    _format = None

@validate.when(_DateTimeMarker)
def validate_dt(dispgraph, value, **kwargs):
    if not isinstance(value, dispgraph.marker._dt_type):
        raise Invalid("type_error")

@dictify.when(_DateTimeMarker)
def dictify_dt(dispgraph, value, **kwargs):
    return unicode(value.isoformat())

@undictify.when(_DateTimeMarker)
def undictify_dt(dispgraph, value, **kwargs):
    marker = dispgraph.marker
    return _parse(value, marker._dt_type)

class DateTime(_DateTimeMarker):
    _dt_type = datetime.datetime

class Date(_DateTimeMarker):
    _dt_type = datetime.date

class Time(_DateTimeMarker):
    _dt_type = datetime.time

class TimeDelta(Leaf):
    pass

@validate.when(TimeDelta)
def validate_td(dispgraph, value, **kwargs):
    if not isinstance(value, datetime.timedelta):
        raise Invalid("type_error")

@dictify.when(TimeDelta)
def dictify_dt(dispgraph, value, **kwargs):
    return (value.minutes, value.seconds, value.microseconds)

@undictify.when(TimeDelta)
def undictify_dt(dispgraph, value, **kwargs):
    if not isinstance(value, (list, tuple)):
        raise Invalid("type_error", "Expected list or tuple, got {}".format(type(value)))
    if len(value != 3):
        raise Invalid("value_error", "Expected 3 items, not {}".format(len(value)))
    try:
        return dt.timedelta(*value)
    except TypeError as e:
        raise Invalid("type_error", str(e))

def _parse(value, cls=datetime.datetime):
    '''
    >>> _parse("2001-01-01T5:10:15")
    datetime.datetime(2001, 1, 1, 5, 10, 15)
    >>> _parse("2001-01-01", datetime.date)
    datetime.date(2001, 1, 1)
    >>> _parse("5:10:15", datetime.time)
    datetime.time(5, 10, 15)
    >>> _parse("5:10:15.42", datetime.time)
    datetime.time(5, 10, 15, 420000)
    >>> _parse("5:10:15.42", datetime.timedelta)
    Traceback (most recent call last):
        ...
    ValueError: Unrecognized date type: <type 'datetime.timedelta'>
    '''
    if cls is datetime.datetime:
        fmt = "%Y-%m-%dT%H:%M:%S"
    elif cls is datetime.date:
        fmt = "%Y-%m-%d"
    elif cls is datetime.time:
        fmt = "%H:%M:%S"
    else:
        raise ValueError("Unrecognized date type: {}".format(cls))
    if isinstance(value, cls):
        return value
    if not isinstance(value, basestring):
        raise Invalid("type_error")
    if '.' in value and cls in [datetime.datetime, datetime.time]:
        fmt = fmt + ".%f"
    try:
        val = datetime.datetime.strptime(value, fmt)
    except ValueError as e:
        raise Invalid("bad_format", str(e))
    if cls is datetime.datetime:
        return val
    elif cls is datetime.date:
        return val.date()
    else:
        return val.time()
