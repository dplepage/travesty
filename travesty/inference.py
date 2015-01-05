'''Tools for inferring the best marker for an object

>>> infer_marker(True)
<Boolean>
>>> infer_marker(12)
<Int>
>>> infer_marker("hello")
<String>
>>> infer_marker([1,2,3])
Traceback (most recent call last):
    ...
NotImplementedError: <type 'list'>
'''
import datetime
import sys

from .cantrips.dispatcher import Dispatcher
from . import Boolean, Complex, Date, DateTime, Int, Number, String, Time

if sys.version >= '3': # pragma: no cover
    unicode = str
    basestring = str


basic_mapping = {
    bool: Boolean(),
    complex: Complex(),
    datetime.date: Date(),
    datetime.time: Time(),
    datetime.datetime: DateTime(),
    int: Int(),
    float: Number(),
    basestring: String(),
}

infer_marker = Dispatcher()

@infer_marker.default()
def infer_basic(d, value):
    for typ in type(value).__mro__:
        if typ in basic_mapping:
            return basic_mapping[typ]
    msg = "Cannot infer marker for type {}."
    raise NotImplementedError(msg.format(type(value)))


# TODO infer_typegraph for more complex structures?
# We'll see if we have a use for that.