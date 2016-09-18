from contextlib import contextmanager

import vertigo as vg

from .cantrips.dispatcher import Dispatcher
from .cantrips.subclass import SubclassMixin
from .dispatch_graph import DynamicDispatchGraph
from .invalid import InvalidAggregator

class Marker(SubclassMixin):
    '''This is a placeholder type for all types used as typemarkers.'''
    def __str__(self):
        return "<{}>".format(type(self).__name__)
    def __repr__(self):
        return str(self)

class Leaf(Marker):
    '''The base for all types that don't have children.'''

class Traversable(object):
    '''Any type that knows its own typegraph.

    All subclasses MUST set cls.typegraph to a valid typegraph.
    '''

to_typegraph = Dispatcher()
'''to_typegraph converts objects into typegraphs.

A Vertigo graph is assumed to already be typegraphs and is passed through.
A Marker gets wrapped in a PlainGraphNode.
A Traversable class T is mapped to T.typegraph.

This function is used in several places where typegraphs are needed, so that
you can say e.g. List().of(Int()) instead of the considerably more verbose
List().of(vg.PlainGraphNode(Int())).

Note also that in general any type like List that expects the typegraph to have
children will implement a method called .of() to help you make typegraphs.
'''

cls_to_typegraph = Dispatcher(keyfn=lambda t:t.__mro__)
_c2t = dict()

def associate_typegraph(cls, typegraph):
    '''associate_typegraph lets you map classes to typegraphs.

    It's used by to_typegraph, and provides a convenient way to extend
    to_typegraph for non-Traversable types.

    For example, suppose you have a namedtuple class and an associated typegraph:

    >>> from collections import namedtuple
    >>> import travesty as tv
    >>> Point3 = namedtuple('Point3', ['x', 'y', 'z'])
    >>> P3TG = tv.NamedTuple(Point3).of(x=tv.Int(), y=tv.Int(), z=tv.Int())

    To work with objects of this type, you'd need to pass in the typegraph
    everywhere:

    >>> tv.undictify(P3TG, (1,2,3))
    Point3(x=1, y=2, z=3)

    associate_typegraph lets you set this typegraph as the default if you use the
    class itself in a travesty call:

    >>> associate_typegraph(Point3, P3TG)
    >>> tv.undictify(Point3, (1,2,3))
    Point3(x=1, y=2, z=3)
    '''
    _c2t[cls] = to_typegraph(typegraph)

@cls_to_typegraph.when(Traversable)
def traversable_to_typegraph(d, t):
    return t.typegraph

@cls_to_typegraph.default()
def default_cls_to_typegraph(d, t):
    if t in _c2t: return _c2t[t]
    raise NotImplementedError(t)

@to_typegraph.when(vg.GraphNode)
def graphnode_to_typegraph(d, node):
    return node

@to_typegraph.when(Marker)
def marker_to_typegraph(d, marker):
    return vg.PlainGraphNode(marker)

@to_typegraph.when(type)
def type_to_typegraph(d, t):
    return cls_to_typegraph(t)

class GraphDispatcher(Dispatcher):
    '''A dispatcher with a .call better for DispatchGraphs.

    Supports multiple inheritance by e.g. GraphDispatcher([parent1, parent2]).

    Note that make_dispatcher(*parents), defined below, behaves just like
    GraphDispatcher(*parents) except with some common behaviors added to parents
    by default - consider using it when you create your own dispatchers.
    '''
    def __init__(self, parents=None):
        super(GraphDispatcher, self).__init__(parents=parents)

    def sub(self, parents=()):
        '''Create a new dispatcher with the same keyfn and self as a parent.'''
        return type(self)(parents=(self,)+tuple(parents))

    def raw_call(self, graph, *args, **kwargs):
        extras_graphs = kwargs.pop('extras_graphs', {})
        graph = self._mk_graph(graph, extras_graphs)
        return graph(*args, **kwargs)

    def _mk_graph(self, graph, extras_graphs=None):
        return DynamicDispatchGraph(to_typegraph(graph), self, extras_graphs)

class Wrapper(Marker):
    '''A root for all markers that wrap other markers directly.

    All dispatchers will, by default, apply themselves to the Wrapper's .marker
    attr. This is a convenient way to augment the behavior of a marker - make a
    wrapper around it, then add behavior to a dispatcher for your wrapper. All
    other dispatchers will simply ignore the wrapper, treating it like it were
    its .marker.

    Dan notes:
    I've gone back and forth several times on whether Wrappers should actually
    have handles on their markers or just be nodes in the graph with .sub being
    the interior wrapper. I eventually decided to go this route mainly because
    it means that you can use graphize to zip an object to its typegraph; if a
    Wrapper is an actual separate node that just gets skipped, then that zip is
    no longer possible.
    '''

    def __init__(self, marker):
        assert isinstance(marker, Marker), (
            "Wrapper must be applied to a Marker. To wrap a full graph, use "
            "Wrapper.wrap(graph).")
        self.marker = marker

    @classmethod
    def wrap(cls, t, **kwargs):
        typegraph = to_typegraph(t)
        value = cls(marker=typegraph.value, **kwargs)
        # The ValueOverlay is important (instead of just making a
        # PlainGraphNode) in case the wrapped typegraph is dynamic or isn't yet
        # fully constructed (e.g. a recursive SchemaObj)
        return vg.ValueOverlay(typegraph, value)

    @classmethod
    def factory(cls, *args, **kwargs):
        return lambda m: cls(m, *args, **kwargs)

    def __str__(self):
        return "<{}({})>".format(
            type(self).__name__,
            str(self.marker).strip('<>'))

unwrap = Dispatcher(keyfn=lambda x:type(x).__mro__)
'''Unwrap a marker with Wrappers on it.

When called with only one argument m, unwrap removes all wrappers from m,
returning the innermost marker.

When called with a second argument `type`, unwrap removes wrappers until it
finds one of this type, at which point it returns it. If none is found, it will
return None.

Note that travesty's GraphDispatchers will recurse into Wrappers automatically
by default, so this function is generally not needed in a GraphDispatcher.
'''
@unwrap.when(Marker)
def return_the_marker(d, marker, type=None):
    if type is None or isinstance(marker, type):
        return marker
    return None

@unwrap.when(Wrapper)
def get_wrapped_marker(d, wrapper, type=None):
    if type is not None and isinstance(wrapper, type):
        return wrapper
    return d(wrapper.marker, type)

def core_marker(marker):
    return unwrap(marker)

# Base dispatcher for all travesty-provided types. Adding new functionality to
# this dispatcher is generally a bad idea unless you know what you're doing.
# When you add a new function to this dispatcher, it will be added to graphize,
# dictify, undictify, and validate. It should therefore be very general -
# ideally the signature should be def f(dispgraph, *args, **kwargs), so that any
# other sub-dispatchers' arguments will be unaffected by it. See e.g.
# pass_through_wrapper below.
base_dispatcher = GraphDispatcher()

@base_dispatcher.when(Wrapper)
def pass_through_wrapper(dispgraph, *args, **kwargs):
    '''By default, all travesty dispatchers simple pass through Wrappers.

    This allows you to add custom behavior for certain dispatchers by
    subclassing Wrapper and customizing only the dispatcher you care about.

    For example, a wrapper might have a bunch of extra validation functions;
    graphize, dictify, etc. will ignore these and continue on to the base type,
    but you'd customize validate to run the extra validation functions.
    '''
    return dispgraph.inner(*args, **kwargs)


def make_dispatcher(parents=()):
    '''Create a new graph dispatcher.

    The graph dispatcher will inherit from base_dispatcher as well as any
    parents you specify.
    '''
    return GraphDispatcher(parents = parents + (base_dispatcher,))


# The core methods provided by travesty
# graphize wraps an object in a vertigo graph. If the zipval extras_graph is
# passed in, the returned graph's values will be tuples of (object, zipval).
graphize = make_dispatcher()
@graphize.when(Leaf)
def graphize_object(dispgraph, value, **kwargs):
    '''Default: wrap object in leaf node'''
    if 'zipval' in dispgraph.extras:
        return vg.PlainGraphNode((value, dispgraph.extras.zipval))
    return vg.PlainGraphNode(value)

IGNORE = 0
CHECK = 1
CHECK_ALL = 2

@contextmanager
def aggregating_errors(error_mode):
    if error_mode == IGNORE:
        yield None
    else:
        agg = InvalidAggregator(autoraise=error_mode==CHECK)
        with agg.checking():
            yield agg
        agg.raise_if_any()

# traverse simply walks a value.
traverse = make_dispatcher()
@traverse.when(Marker)
def traverse_object(dispgraph, value, **kwargs):
    pass

# validate traverses and complains if an object is invalid
validate = traverse.sub()
# We wrap it to get CHECK_ALL by default
validate.default_value('error_mode', CHECK_ALL)

# clone copies an object
clone = make_dispatcher()

# mutate updates an object in-place, as best as possible
mutate = clone.sub()

# dictify turns an object into a JSON-serializable structure
dictify = clone.sub()

# undictify is the inverse of dictify
undictify = clone.sub()
# We wrap it to get CHECK_ALL by default
undictify.default_value('error_mode', CHECK_ALL)

# Leaves are passed through clone et al. by default
@clone.when(Leaf)
def passthrough_tl(dispgraph, value, **kwargs):
    return value
