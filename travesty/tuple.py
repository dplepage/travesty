import vertigo as vg

from .base import Marker, to_typegraph
from .base import traverse, validate, dictify, undictify
from .invalid import Invalid, InvalidAggregator

class Tuple(Marker):
    '''The following docstring is ENTIRELY SUSPECT. TODO: Fix it.

    Dictifier for tuples.

    >>> from . import Complex, Int
    >>> t = Tuple.mkgraph((Int(), Complex()))
    >>> dictify(t, (2, 3j))
    (2, 3j)
    >>> undictify(t, (7, 8+2j))
    (7, (8+2j))
    >>> print(vg.ascii_tree(traverse(t, ("7", "8+2j")), sort=True))
    root: ('7', '8+2j')
      +--0: '7'
      +--1: '8+2j'

    >>> undictify(t, 7j)
    Traceback (most recent call last):
        ...
    Invalid: not_iterable
    >>> undictify(t, (1,))
    Traceback (most recent call last):
        ...
    Invalid: bad_len
    >>> validate(t, (6, 1))
    >>> validate(t, 3)
    Traceback (most recent call last):
        ...
    Invalid: not_iterable
    >>> validate(t, ("this", "tuple", "is", "too", "long"))
    Traceback (most recent call last):
        ...
    Invalid: bad_len
    >>> validate(t, (1.5, "hello"))
    Traceback (most recent call last):
        ...
    Invalid: 0: [type_error], 1: [type_error]

    It does support naming the attributes for the purposes of error reporting
    and walking the tree; see also the NamedTuple dfier.

    >>> t2 = Tuple(field_names=("num", "cnum")).of(num=Int(),cnum=Complex())
    >>> validate(t2, (1.5, "hello"))
    Traceback (most recent call last):
        ...
    Invalid: cnum: [type_error], num: [type_error]

    You must provide either a number of fields or a set of field names:

    >>> Tuple()
    Traceback (most recent call last):
        ...
    ValueError: nfields or field_names is required.
    '''
    def __init__(self, nfields=None, field_names=None):
        super(Tuple, self).__init__()
        if field_names is None:
            if nfields is None:
                raise ValueError("nfields or field_names is required.")
            field_names = [str(i) for i in range(nfields)]
        if nfields is None:
            nfields = len(field_names)
        self.field_names = field_names
        self.nfields = nfields

    def of(self, **kwargs):
        children = {key:to_typegraph(val) for key, val in kwargs.items()}
        return vg.PlainGraphNode(self, children)

    @classmethod
    def mkgraph(cls, type_tuple):
        # type_tuple should be a tuple of typegraphs
        children = {str(k):val for k, val in enumerate(type_tuple)}
        return cls(nfields=len(type_tuple)).of(**children)


@dictify.when(Tuple)
def dictify_tuple(dispgraph, value, **kw):
    names = dispgraph.marker.field_names
    return tuple(dispgraph[name](v, **kw) for name,v in zip(names, value))

@undictify.when(Tuple)
def undictify_tuple(dispgraph, value, **kw):
    names = dispgraph.marker.field_names
    try:
        if len(value) != len(names):
            raise Invalid('bad_len')
    except TypeError:
        raise Invalid('not_iterable')
    error_agg = InvalidAggregator(autoraise = kw.get('fail_early', False))
    l = []
    for (n, val) in zip(names, value):
        with error_agg.checking_sub(n):
            l.append(dispgraph[n](val, **kw))
    error_agg.raise_if_any()
    return tuple(l)

@validate.when(Tuple)
def validate_tuple(dispgraph, value, **kw):
    names = dispgraph.marker.field_names
    try:
        if len(value) != len(names):
            raise Invalid('bad_len')
    except TypeError:
        raise Invalid('not_iterable')
    error_agg = InvalidAggregator(autoraise = kw.get('fail_early', False))
    for (n, val) in zip(names, value):
        with error_agg.checking_sub(n):
            dispgraph[n](val, **kw)
    error_agg.raise_if_any()

@traverse.when(Tuple)
def traverse_tuple(dispgraph, value, zipgraph=None, **kwargs):
    def get(key):
        if hasattr(value, key):
            return getattr(value, key)
        try:
            key = int(key)
        except:
            raise AttributeError("'{}' object has no attribute '{}'".format(type(value), key))
        return value[key]
    edges = []
    names = dispgraph.marker.field_names
    for key in names:
        subgraph = dispgraph[key]
        subzip = zipgraph[key] if zipgraph else None
        edges.append((key, subgraph(get(key), subzip, **kwargs)))
    v = value
    if zipgraph:
        v = (v, zipgraph.value)
    return vg.PlainGraphNode(v, edges)



class NamedTuple(Tuple):
    '''
    Like Tuple, but for namedtuple instances:

    >>> from collections import namedtuple
    >>> from . import Complex, Int
    >>> WeirdPoint = namedtuple("WeirdPoint", ["num", "cnum"])
    >>> t = NamedTuple(WeirdPoint).of(num=Int(), cnum=Complex())
    >>> p = WeirdPoint(3, 6j)
    >>> dictify(t, p)
    (3, 6j)
    >>> undictify(t, (5, 2+1.0j))
    WeirdPoint(num=5, cnum=(2+1j))
    >>> validate(t, p)
    >>> g = vg.from_dict(dict(num="A Number", cnum="A Complex Number"))
    >>> print(vg.ascii_tree(traverse(t, p, zipgraph=g)))
    root: (WeirdPoint(num=3, cnum=6j), None)
      +--num: (3, 'A Number')
      +--cnum: (6j, 'A Complex Number')

    Note that validate explicitly expects the particular namedtuple class, and
    won't settle even for an identical one:

    >>> WeirdPoint2 = namedtuple("WeirdPoint", ["num", "cnum"])
    >>> validate(t, WeirdPoint2(3, 6j))
    Traceback (most recent call last):
        ...
    Invalid: type_error
    '''
    def __init__(self, tuple_type):
        super(NamedTuple, self).__init__(field_names=tuple_type._fields)
        self.tuple_type = tuple_type

@validate.when(NamedTuple)
def validate_namedtuple(dispgraph, value, **kw):
    tuple_type = dispgraph.marker.tuple_type
    if not isinstance(value, tuple_type):
        raise Invalid('type_error')
    dispgraph.super(NamedTuple)(value, **kw)


@undictify.when(NamedTuple)
def undictify_namedtuple(dispgraph, value, **kw):
    t = dispgraph.super(NamedTuple)(value, **kw)
    return dispgraph.marker.tuple_type._make(t)
