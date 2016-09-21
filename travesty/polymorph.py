import vertigo as vg

from .base import Marker, Traversable, to_typegraph, IGNORE
from .base import graphize, validate, clone, dictify, undictify
from .invalid import Invalid


class UnknownType(Exception):
    '''Raised when a Polymorph encounters an unknown type.'''
    pass


class Polymorph(Marker):
    '''
    A marker for selecting between several types.

    Generally you want to assemble these using .mkgraph, which takes a mapping
    from string names to either traversable types or (types, typegraph) pairs.

    When operating on an object, the Polymorph will select which of its child
    typegraphs to use based on the type of the object it encounters; when
    dictifying, it will store the string name so that later undictification can
    determine what type was here.

    For example, consider a simple Point type:

    >>> import travesty as tv
    >>> class Point(tv.SchemaObj):
    ...     field_types = dict(x=tv.Number(), y=tv.Complex())
    ...     def __repr__(self): return "Point({}, {})".format(self.x, self.y)
    ...

    We can create a typegraph representing a value that could be a Point or a
    plain number as follows:

    >>> NumOrPoint = Polymorph.mkgraph({
    ...     'point':Point,
    ...     'num':((int, float), tv.Number()),
    ... })

    This typegraph indicates that values of type Point should be processed using
    Point's typegraph, and values of type int or float should be processed using
    the typegraph Number() (well, to_typegraph(Number())). This means that
    various dispatchers can be used on both types:

    >>> tv.clone(NumOrPoint, 12)
    12
    >>> tv.clone(NumOrPoint, Point(x=1, y=2))
    Point(1, 2)
    >>> tv.validate(NumOrPoint, 12)
    >>> tv.validate(NumOrPoint, Point(x=1, y=2))

    Validate and other error-checking will fail on unknown types:

    >>> tv.validate(NumOrPoint, "blah")
    Traceback (most recent call last):
    ...
    Invalid: type_error - Unrecognized type: <type 'str'>
    >>> tv.clone(NumOrPoint, "blah")
    Traceback (most recent call last):
    ...
    UnknownType: str
    >>> tv.clone(NumOrPoint, "blah", error_mode=tv.CHECK)
    Traceback (most recent call last):
    ...
    Invalid: type_error: Unrecognized type: <type 'str'>

    Dictify returns a tuple of (type id, dictified value), so that you can later
    determine what type you had:

    >>> tv.dictify(NumOrPoint, 12)
    ('num', 12)
    >>> dictify(NumOrPoint, 3.5)
    ('num', 3.5)
    >>> dictify(NumOrPoint, Point(x=1, y=3)) == ('point', {'x':1, 'y':3})
    True

    Undictify expects such a tuple:

    >>> tv.undictify(NumOrPoint, ('num', 42))
    42
    >>> p = tv.undictify(NumOrPoint, ('point', {'x':-1, 'y':2+2j}))
    >>> p.x
    -1
    >>> p.y
    (2+2j)

    The input to undictify MUST be a list or tuple of length 2, and the first
    item must be known to the Polymorph:

    >>> tv.undictify(NumOrPoint, 42)
    Traceback (most recent call last):
        ...
    Invalid: type_error
    >>> tv.undictify(NumOrPoint, ('num', 42, 'something extra for no reason'))
    Traceback (most recent call last):
        ...
    Invalid: bad_list
    >>> tv.undictify(NumOrPoint, ('weird_key', 42))
    Traceback (most recent call last):
        ...
    Invalid: bad_typename - weird_key
    >>> tv.undictify(NumOrPoint, ('weird_key', 42), error_mode=IGNORE)
    Traceback (most recent call last):
        ...
    KeyError: weird_key

    Traversal with zipvals expects the graph to have keys matching the main
    graph structure, as always, but note that the graph value at the actual
    Polymorph will be ignored:

    >>> g = vg.from_dict(dict(_self="Ignored", num="A number", point=dict(
    ... _self="A Point", x="The X", y="The Y")))
    >>> print(vg.ascii_tree(graphize(NumOrPoint, 3, extras_graphs=dict(zipval=g))))
    root: (3, 'A number')
    >>> print(vg.ascii_tree(graphize(NumOrPoint, p, extras_graphs=dict(zipval=g)), sort=True))
    root: (Point(-1, (2+2j)), 'A Point')
      +--x: (-1, 'The X')
      +--y: ((2+2j), 'The Y')

    Note that the initialization above is short for the longer form:
    >>> NumOrPoint = Polymorph({'point':Point, 'num':(int, float)}).of(
    ...     point = Point, num=tv.Number()
    ... )


    '''
    def __init__(self, mapping):
        super(Polymorph, self).__init__()
        self.cls_to_name = {}
        for name, classes in mapping.items():
            if not isinstance(classes, (list, tuple)):
                classes = (classes,)
            for cls in classes:
                self.cls_to_name[cls] = name

    def name_for_type(self, typ):
        '''Given a type, get the corresponding name.'''
        for basetype in typ.__mro__:
            if basetype in self.cls_to_name:
                return self.cls_to_name[basetype]
        raise UnknownType(typ.__name__)

    def name_for_val(self, value):
        '''Given an object, get the corresponding name.'''
        return self.name_for_type(type(value))

    def of(self, **kw):
        children = {key:to_typegraph(val) for key, val in kw.items()}
        return vg.PlainGraphNode(self, **children)

    @classmethod
    def mkgraph(cls, mapping):
        # Mapping should be name:(type_or_types, typegraph) or name:Traversable
        lookup = {}
        children = {}
        for name, data in mapping.items():
            if isinstance(data, type) and issubclass(data, Traversable):
                lookup[name] = (data,)
                children[name] = data.typegraph
            else:
                lookup[name], children[name] = data
        return cls(lookup).of(**children)


def apply_pmorph(dispgraph, value, error_mode=IGNORE, **kw):
    '''Returns (name, dictified_value), where name is the polymorphic id.'''
    kw['error_mode'] = error_mode
    try:
        name = dispgraph.marker.name_for_val(value)
    except UnknownType:
        if error_mode == IGNORE:
            raise
        raise Invalid("type_error", "Unrecognized type: {}".format(type(value)))
    value = dispgraph[name](value, **kw)
    return (name, value)


@clone.when(Polymorph)
def clone_pmorph(dispgraph, value, error_mode=IGNORE, **kw):
    name, value = apply_pmorph(dispgraph, value, error_mode, **kw)
    return value


@dictify.when(Polymorph)
def dictify_pmorph(dispgraph, value, error_mode=IGNORE, **kw):
    '''Returns (name, dictified_value), where name is the polymorphic id.'''
    return apply_pmorph(dispgraph, value, error_mode, **kw)


@undictify.when(Polymorph)
def undictify_pmorph(dispgraph, value, error_mode=IGNORE, **kw):
    kw['error_mode'] = error_mode
    if error_mode != IGNORE:
        if not isinstance(value, (list, tuple)):
            raise Invalid('type_error')
        if len(value) != 2:
            raise Invalid('bad_list')
    name, value = value
    if error_mode != IGNORE and name not in dispgraph:
        raise Invalid('bad_typename', name)
    return dispgraph[name](value, **kw)


@validate.when(Polymorph)
def validate_pmorph(dispgraph, value, **kw):
    apply_pmorph(dispgraph, value, **kw)


@graphize.when(Polymorph)
def graphize_pmorph(dispgraph, value, **kw):
    name = dispgraph.marker.name_for_val(value)
    return dispgraph[name](value, **kw)
