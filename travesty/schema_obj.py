from __future__ import absolute_import

import vertigo as vg

from .cantrips.immutable_dict import ImmutableDict
from .cantrips.subclass import Subclassable

from .base import Traversable, to_typegraph
from .object_marker import ObjectMarker

def _marker_for(cls):
    '''Get a marker for a SchemaObj subclass.

    The returned marker will be a subclass of ObjectMarker targeting the input
    class.
    '''
    bases = []
    for base in cls.__bases__:
        if issubclass(base, SchemaObj):
            bases.append(base.marker_cls)
    if not bases:
        bases = [ObjectMarker]
    return type(cls.__name__+"Marker", tuple(bases), dict(target_cls=cls))

class SchemaObj(Traversable, Subclassable):
    '''Type for making python classes with automatically-inferred typegraphs.

    The class attribute field_types should be a dictionary mapping attribute
    names to typegraphs (or valid targets for to_typegraph). Some metaclass
    magic will automatically generate the class attributes .marker_cls and
    .typegraph, where .marker_cls is an ObjectMarker subclass pointing at this
    type, and .typegraph is a typegraph whose root contains an instance of
    cls.marker_cls and whose children are determined by cls.field_types.

    To support recursive types, you can specify a single-argument callable for
    field_types, which takes the class and returns a valid field_types dict. If
    you use this method, the class will also get a classmethod called
    finalize_typegraph which MUST be called before you do anything significant
    with the class. Before this function is called, cls.typegraph will have no
    children; when you call finalize_typegraph, the children will be populated
    and the finalize_typegraph method will be removed.
    '''
    field_types = ImmutableDict()

    def __init__(self, **kwargs):
        for key in self.field_types:
            if key not in kwargs:
                kwargs[key] = None
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def __subclass__(cls, field_types=None, **kwargs):
        super(SchemaObj, cls).__subclass__(**kwargs)
        cls.marker_cls = _marker_for(cls)
        # It is CRUCIAL that we set cls.typegraph now instead of in
        # finalize_typegraph in case something needs the graph before then.
        cls.typegraph = vg.PlainGraphNode(cls.marker_cls())
        if callable(field_types):
            @classmethod
            def finalize_typegraph(cls):
                cls.__construct_typegraph(field_types(cls))
                del cls._finalize_typegraph
            cls._finalize_typegraph = finalize_typegraph
        else:
            cls.__construct_typegraph(field_types)

    @classmethod
    def __construct_typegraph(cls, field_types):
        if field_types is None:
            field_types = {}
        cls._field_types = field_types
        cls.field_types = cls.field_types.overlay(field_types, strip_none=True)
        for key, value in cls.field_types.items():
            cls.typegraph[key] = to_typegraph(value)


# Force SchemaObj to set itself up
SchemaObj.__subclass__()

