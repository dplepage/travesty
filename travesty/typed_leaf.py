'''
TypedLeaf: a marker for typechecking leaves.

>>> int_or_bool = TypedLeaf(int, bool)
>>> validate(int_or_bool, 12)
>>> validate(int_or_bool, True)
>>> validate(int_or_bool, "12")
Traceback (most recent call last):
...
Invalid: type_error

>>> try:
...     validate(int_or_bool, "12")
... except Invalid as e:
...     print(e)
type_error - Expected one of [int, bool]; got str

dictify and undictify always pass through values unchanged, regardless of type:

>>> dictify(int_or_bool, True)
True
>>> dictify(int_or_bool, "Not a bool")
'Not a bool'
>>> undictify(int_or_bool, 100)
100
>>> undictify(int_or_bool, "100")
'100'

Additionally, this module provides several TypedLeaf subclasses with the types
prefilled:

>>> s = String()
>>> validate(s, "foo")
>>> validate(s, 12)
Traceback (most recent call last):
...
Invalid: type_error

>>> b = Boolean()
>>> validate(b, True)
>>> validate(b, False)
>>> validate(b, 1)
Traceback (most recent call last):
...
Invalid: type_error

>>> i = Int()
>>> validate(i, 12)
>>> validate(i, 12.1)
Traceback (most recent call last):
...
Invalid: type_error

>>> num = Number()
>>> validate(num, 1)
>>> validate(num, 1.1)
>>> validate(num, 1+1j)
Traceback (most recent call last):
...
Invalid: type_error
>>> validate(num, 'ten')
Traceback (most recent call last):
...
Invalid: type_error

>>> com = Complex()
>>> validate(com, 1)
>>> validate(com, 1.1)
>>> validate(com, 1+1j)
>>> validate(com, 'ten')
Traceback (most recent call last):
...
Invalid: type_error

'''

import numbers
import sys

if sys.version < '3': # pragma: no cover
    bytes_type = str
else: # pragma: no cover
    bytes_type = bytes
    basestring = str

from .base import Leaf, dictify, undictify, validate, IGNORE, CHECK
from .invalid import Invalid

def _type_to_str(typ):
    return getattr(typ, '__name__', str(typ))

class TypedLeaf(Leaf):
    '''Marker for simple types, such as integers and strings.

    Parameterized by a list of allowed types.

    TypedLeaf(*types) simply means "A value of one of these types."
    '''
    def __init__(self, *types):
        if types:
            self.types = types

    def error_msg_for(self, value):
        '''
        >>> TypedLeaf().error_msg_for(12)
        'Expected nothing; got int'
        >>> TypedLeaf(bool).error_msg_for(12)
        'Expected bool; got int'
        >>> TypedLeaf(str, dict).error_msg_for(12)
        'Expected one of [str, dict]; got int'
        '''
        got = _type_to_str(type(value))
        if not self.types: # This shouldn't really happen
            expected = 'nothing'
        elif len(self.types) == 1:
            expected = _type_to_str(self.types[0])
        else:
            tstr = ', '.join(_type_to_str(t) for t in self.types)
            expected = 'one of [{}]'.format(tstr)
        return 'Expected {}; got {}'.format(expected, got)

    types = None

# validate checks .types,

@validate.when(TypedLeaf)
def validate_tl(dispgraph, value, **kwargs):
    if kwargs.get('error_mode', CHECK) == IGNORE:
        # why would you call validate with error_mode IGNORE? Nonetheless, it'll
        # do what you apparently want.
        return
    if not isinstance(value, dispgraph.marker.types):
        raise Invalid('type_error', dispgraph.marker.error_msg_for(value))

Boolean = TypedLeaf.subclass(types=(bool,), __class_name="Boolean")
String = TypedLeaf.subclass(types=(basestring,), __class_name="String")
Bytes = TypedLeaf.subclass(types=(bytes_type,), __class_name="Bytes")
Int = TypedLeaf.subclass(types=(numbers.Integral,), __class_name="Int")
Number = TypedLeaf.subclass(types=(numbers.Real,), __class_name="Number")
Complex = TypedLeaf.subclass(types=(numbers.Complex,), __class_name="Complex")

# temporary hack for JSON compatilibity
# TODO make a separate JSON-aware dfier?
import base64

@dictify.when(Bytes)
def df_bytes(dispgraph, value, **kwargs):
    '''
    >>> dictify(Bytes(), b'\\xc3\\xbf') == u'w78='
    True
    '''
    return base64.b64encode(value).decode('ascii')

@undictify.when(Bytes)
def udf_bytes(dispgraph, value, **kwargs):
    '''
    >>> undictify(Bytes(), u'w78=') == b'\\xc3\\xbf'
    True
    >>> undictify(Bytes(), 'invalid_base64\\xc3')
    Traceback (most recent call last):
        ...
    Invalid: ...
    >>> undictify(Bytes(), ['not', 'a', 'string'])
    Traceback (most recent call last):
        ...
    Invalid: ...
    '''
    try:
        return base64.b64decode(value)
    except Exception as e:
        raise Invalid("bad_value", str(e))
