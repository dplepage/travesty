import vertigo as vg

from .cantrips.empty_instance import create_instance

from .base import traverse, validate, dictify, undictify, to_typegraph
from .invalid import Invalid, InvalidAggregator
from .schema import Schema

class ObjectMarker(Schema):
    '''Marker for objects that can be assembled by field.

    The Marker is parameterized by a target_cls, which determines what type is
    expected.

    The children of an ObjectMarker node in the typegraph identify the salient
    attributes of the target_cls; dictify will use getattr to extract and store
    those attributes, and undictify will unpack the stored attributes and pass
    them into the marker's .construct function to produce an object with those
    attrs.

    By default, the .construct uses the empty_instance cantrip, which creates
    blank copies of objects and then sets attributes on them in order to bypass
    any side-effects of the class's __init__ function:

    >>> from . import Int
    >>> class Pair(object):
    ...     def __init__(self, x, y):
    ...         print("Creating a pair!")
    ...         self.x, self.y = x, y
    ...     def __repr__(self):
    ...         return 'Pair({!r}, {!r})'.format(self.x, self.y)
    >>> int_pair = ObjectMarker(Pair).of(
    ...     x = Int(),
    ...     y = Int(),
    ... )
    >>> p1 = Pair(2,4)
    Creating a pair!
    >>> p2 = undictify(int_pair, dict(x=2, y=4))
    >>> (p2.x, p2.y) == (p1.x, p1.y)
    True
    >>> undictify(int_pair, (2,4))
    Traceback (most recent call last):
        ...
    Invalid: type_error - Expected a dict, got <type 'tuple'> instead

    You can also give an ObjectMarker a custom construct, which must accept
    keyword arguments of all the typegraph keys.

    >>> int_pair2 = ObjectMarker(Pair, constructor=Pair).of(
    ...     x = Int(),
    ...     y = Int()
    ... )
    >>> p3 = undictify(int_pair2, dict(x=2, y=4))
    Creating a pair!
    >>> (p3.x, p3.y) == (p1.x, p1.y)
    True

    Validate and traverse work as you'd expect:

    >>> validate(int_pair, p3)
    >>> invalid_p = Pair("hi", "ho")
    Creating a pair!
    >>> validate(int_pair, invalid_p)
    Traceback (most recent call last):
        ...
    Invalid: x: [type_error], y: [type_error]
    >>> validate(int_pair, (4,5))
    Traceback (most recent call last):
        ...
    Invalid: type_error - Expected Pair, got tuple

    >>> print(vg.ascii_tree(traverse(int_pair, p3), sort=True))
    root: Pair(2, 4)
      +--x: 2
      +--y: 4


    '''
    target_cls = None

    def construct(self, object_kwargs, **kwargs):
        if self.constructor:
            return self.constructor(**object_kwargs)
        return create_instance(self.target_cls, object_kwargs)

    def __init__(self, target_cls=None, constructor=None):
        if target_cls is not None:
            self.target_cls = target_cls
        self.constructor = constructor

    def of(self, **kwargs):
        children = {key:to_typegraph(val) for key, val in kwargs.items()}
        return vg.PlainGraphNode(self, **children)

def _as_dict(dispgraph, value, raise_invalid=False):
    result = {}
    for attr in dispgraph.key_iter():
        if raise_invalid and not hasattr(value, attr):
            raise Invalid("missing_attr", "Missing attribute {}".format(attr))
        result[attr] = getattr(value, attr)
    return result

@traverse.when(ObjectMarker)
def traverse_obj(dispgraph, value, zipgraph=None, **kwargs):
    d = _as_dict(dispgraph, value)
    g = dispgraph.super(ObjectMarker)(d, zipgraph, **kwargs)
    g.value = value if zipgraph is None else (value, zipgraph.value)
    return g

@validate.when(ObjectMarker)
def validate_obj(dispgraph, value, **kwargs):
    marker = dispgraph.marker
    if not isinstance(value, marker.target_cls):
        name = type(value).__name__
        expected = marker.target_cls.__name__
        raise Invalid("type_error", "Expected {}, got {}".format(expected, name))
    d = _as_dict(dispgraph, value, True)
    return dispgraph.super(ObjectMarker)(d, **kwargs)

@dictify.when(ObjectMarker)
def dictify_obj(dispgraph, value, **kwargs):
    d = _as_dict(dispgraph, value)
    return dispgraph.super(ObjectMarker)(d, **kwargs)

@undictify.when(ObjectMarker)
def undictify_obj(dispgraph, value, **kwargs):
    marker = dispgraph.marker
    error_agg = InvalidAggregator(autoraise = kwargs.get('fail_early', False))
    with error_agg.checking():
        result = dispgraph.super(ObjectMarker)(value, **kwargs)
    error_agg.raise_if_any()
    extra_keys = set(value.keys()) - set(dispgraph.key_iter())
    if extra_keys:
        error_agg.own_error(Invalid('unexpected_fields', keys=extra_keys))
    error_agg.raise_if_any()
    return marker.construct(result, **kwargs)

