import vertigo as vg

from .base import Marker, to_typegraph, IGNORE, aggregating_errors
from .base import graphize, validate, dictify, clone, traverse
from .invalid import Invalid

class Tuple(Marker):
    '''The following docstring is ENTIRELY SUSPECT. TODO: Fix it.

    Dictifier for tuples.

    >>> from . import Complex, Int, undictify
    >>> t = Tuple.mkgraph((Int(), Complex()))
    >>> dictify(t, (2, 3j))
    (2, 3j)
    >>> undictify(t, (7, 8+2j))
    (7, (8+2j))
    >>> print(vg.ascii_tree(graphize(t, ("7", "8+2j")), sort=True))
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

    def of(self, **kw):
        children = {key:to_typegraph(val) for key, val in kw.items()}
        return vg.PlainGraphNode(self, children)

    @classmethod
    def mkgraph(cls, type_tuple):
        # type_tuple should be a tuple of typegraphs
        children = {str(k):val for k, val in enumerate(type_tuple)}
        return cls(nfields=len(type_tuple)).of(**children)

def apply_tuple(dispgraph, value, kw):
    error_mode = kw.get("error_mode", IGNORE)
    names = dispgraph.marker.field_names
    if error_mode == IGNORE:
        return tuple(dispgraph[n](v, **kw) for n,v in zip(names, value))
    try:
        if len(value) != len(names):
            msg = "Expected iterable of length {}, not {}"
            msg = msg.format(len(names), len(value))
            raise Invalid('bad_len', msg=msg, fatal=True)
    except TypeError:
        msg = "Expected iterable, not {}".format(type(value))
        raise Invalid('not_iterable', msg, fatal=True)
    with aggregating_errors(error_mode) as agg:
        l = []
        for (n, val) in zip(names, value):
            with agg.checking_sub(n):
                l.append(dispgraph[n](val, **kw))
        return tuple(l)


@clone.when(Tuple)
def clone_tuple(dispgraph, value, **kw):
    return apply_tuple(dispgraph, value, kw)

@traverse.when(Tuple)
def traverse_tuple(dispgraph, value, **kw):
    apply_tuple(dispgraph, value, kw)

@graphize.when(Tuple)
def graphize_tuple(dispgraph, value, **kw):
    items = apply_tuple(dispgraph, value, kw)
    names = dispgraph.marker.field_names
    edges = zip(names, items)
    if 'zipval' in dispgraph.extras:
        value = (value, dispgraph.extras.zipval)
    return vg.PlainGraphNode(value, edges)


class NamedTuple(Tuple):
    '''
    Like Tuple, but for namedtuple instances:

    >>> from collections import namedtuple
    >>> from . import Complex, Int, undictify
    >>> WeirdPoint = namedtuple("WeirdPoint", ["num", "cnum"])
    >>> t = NamedTuple(WeirdPoint).of(num=Int(), cnum=Complex())
    >>> p = WeirdPoint(3, 6j)
    >>> dictify(t, p)
    (3, 6j)
    >>> undictify(t, (5, 2+1.0j))
    WeirdPoint(num=5, cnum=(2+1j))
    >>> validate(t, p)
    >>> g = vg.from_dict(dict(num="A Number", cnum="A Complex Number"))
    >>> print(vg.ascii_tree(graphize(t, p, extras_graphs=dict(zipval=g))))
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
        msg = "Expected {}, got {}".format(tuple_type, type(value))
        raise Invalid('type_error', msg=msg, fatal=True)
    dispgraph.super(NamedTuple)(value, **kw)


@clone.when(NamedTuple)
def clone_namedtuple(dispgraph, value, **kw):
    t = dispgraph.super(NamedTuple)(value, **kw)
    return dispgraph.marker.tuple_type._make(t)


@dictify.when(NamedTuple)
def df_namedtuple(dispgraph, value, **kw):
    '''Explicit dictify to provide a plain tuple.

    Without this, dictify would fall back on the clone() implementation and
    would therefore return a namedtuple of the appropriate type.

    It's ok that undictify falls back on clone, because cloning a plain tuple
    actually will create an appropriate namedtuple.
    '''
    return dispgraph.super(NamedTuple)(value, **kw)
