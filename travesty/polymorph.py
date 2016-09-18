import vertigo as vg

from .base import Marker, Traversable, to_typegraph, IGNORE
from .base import graphize, validate, clone, dictify, undictify
from .invalid import Invalid


class UnknownType(Exception):
    '''Raised when a Polymorph encounters an unknown type.'''
    pass


class Polymorph(Marker):
    '''The following docstring is ENTIRELY SUSPECT. TODO: Fix it.

    A dictifier that selects between several dictifiables based on classes.

    The mapping argument is a dict whose keys are strings and whose values are
    either (class_list, Dictifier) pairs or Dictifiable classes.

    Polymorph can Dictify any object that is an instance of one of the
    Dictifiable classes or any class in one of the class_list entries; it will
    dictify it as a tuple of (name, value), where name identifies which
    Dictifier was used and value is the dictified object; on undictifiance, it
    undictifies the value using the Dictifier for that name.

    For example:

    >>> from . import Number, Complex, SchemaObj
    >>> class Point(SchemaObj):
    ...     field_types = dict(x=Number(), y=Complex())
    ...     def __repr__(self): return "Point({}, {})".format(self.x, self.y)
    ...
    >>> num_or_point = Polymorph.mkgraph({
    ...     'point':Point,
    ...     'num':((int, float), Number()),
    ... })
    >>> dictify(num_or_point, 12)
    ('num', 12)
    >>> dictify(num_or_point, 3.5)
    ('num', 3.5)
    >>> dictify(num_or_point, Point(x=1, y=3)) == ('point', {'x':1, 'y':3})
    True
    >>> undictify(num_or_point, ('num', 42))
    42
    >>> p = undictify(num_or_point, ('point', {'x':-1, 'y':2+2j}))
    >>> p.x
    -1
    >>> p.y
    (2+2j)

    The input to undictify MUST be a list or tuple of length 2:

    >>> undictify(num_or_point, 42)
    Traceback (most recent call last):
        ...
    Invalid: type_error
    >>> undictify(num_or_point, ('num', 42, 'something extra for no reason'))
    Traceback (most recent call last):
        ...
    Invalid: bad_list

    It will validate only the types in its list:

    >>> validate(num_or_point, 3)
    >>> validate(num_or_point, 3.5)
    >>> validate(num_or_point, p)
    >>> validate(num_or_point, 'hi')
    Traceback (most recent call last):
    ...
    Invalid: type_error - Unrecognized type: <type 'str'>

    Traversal with zipvals expects the graph to have keys matching the main
    graph structure, as always, but note that the graph value at the actual
    Polymorph will be ignored:

    >>> g = vg.from_dict(dict(_self="Ignored", num="A number", point=dict(
    ... _self="A Point", x="The X", y="The Y")))
    >>> print(vg.ascii_tree(graphize(num_or_point, 3, extras_graphs=dict(zipval=g))))
    root: (3, 'A number')
    >>> print(vg.ascii_tree(graphize(num_or_point, p, extras_graphs=dict(zipval=g)), sort=True))
    root: (Point(-1, (2+2j)), 'A Point')
      +--x: (-1, 'The X')
      +--y: ((2+2j), 'The Y')

    Note that the initialization above is short for the longer form:
    >>> num_or_point = Polymorph({'point':Point, 'num':(int, float)}).of(
    ...     point = Point, num=Number()
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
        raise Invalid("type_error", "Unknown type: {}".format(type(value)))
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
    return dispgraph[name](value, **kw)


@validate.when(Polymorph)
def validate_pmorph(dispgraph, value, **kw):
    try:
        name = dispgraph.marker.name_for_val(value)
    except UnknownType:
        raise Invalid("type_error", "Unrecognized type: {}".format(type(value)))
    dispgraph[name](value, **kw)


@graphize.when(Polymorph)
def graphize_pmorph(dispgraph, value, **kw):
    name = dispgraph.marker.name_for_val(value)
    return dispgraph[name](value, **kw)
