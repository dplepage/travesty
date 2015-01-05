import vertigo as vg

from .cantrips.dispatcher import Dispatcher, DispatchSuper, SuperMarker

#  =================
#  = DispatchGraph =
#  =================

# Adding special methods to GraphNodes is discouraged. I'm only doing it here
# because it makes the API MUCH simpler when writing external target functions,
# and in general we don't expect the recieving functions to manipulate these.
class DispatchGraph(object):
    '''Abstract base mixin for dispatch graphs.

    A DispatchGraph is just a wrapper around a graph-aware dispatcher and a
    marker value, with some helpful functions.

    Dispatch Graphs have several core attributes:

    .target - the object to dispatch on (any value or SuperMarker)
    .disp_target - the dispatcher to use (a Dispatcher or a DispatchSuper)
    .value - a tuple of (.target, .disp_target)
    .marker_graph() - the wrapped marker graph

    Subclasses must either provide .value OR both .target and .disp_target. The
    other will be inferred automatically.

    The .marker property exposes the marker value for this node, which is the
    same as .target unless .target is a SuperMarker, in which case .marker is
    the actual marker value that the SuperMarker is wrapping.

    Similarly, the .disp property is the same as .disp_target except when
    .disp_target is a DispatchSuper, when .disp is the root dispatcher instead.

    DispatchGraphs are callable - calling one will use its dispatcher and target
    to choose a function, and then invoke that function.
    '''
    __slots__ = ()

    def __call__(self, *args, **kwargs):
        fn = self._get_fn()
        if not fn:
            raise NotImplementedError(self.marker)
        return fn(self, *args, **kwargs)

    @property
    def target(self):
        return self.value[0]

    @property
    def disp_target(self):
        return self.value[1]

    @property
    def disp(self):
        if isinstance(self.disp_target, DispatchSuper):
            return self.disp_target.disp
        return self.disp_target

    @property
    def value(self):
        return (self.target, self.disp_target)

    @property
    def marker(self):
        if isinstance(self.target, SuperMarker):
            return self.target.val
        return self.target

    def marker_graph(self):
        raise NotImplementedError()

    def _get_fn(self):
        return self.disp_target.dispatch(self.target)

    def for_marker(self, marker):
        '''Overlay a new marker type on this graph.

        The returned graph is functionally identical to this one, but with a
        different marker type at this node.
        '''
        return DispatchOverlay(self, target=marker)

    def super(self, cls):
        '''Get a DispatchGraph for the supertype of this one's target.

        The returned graph is functionally identical to this one, but with a
        super object as its target. The type of the new target is obtained by
        walking up the current marker's __mro__. In particular, if the current
        target is a super instance super(SomeMarker, obj), this will sensibly
        choose the next supertype after SomeMarker in obj's __mro__.
        '''
        return self.for_marker(SuperMarker(cls, self.marker))

    def parent(self, disp):
        '''Get a DispatchGraph for the parent of this one's dispatcher.

        The returned graph is functionally identical to this one, but with a
        different dispatcher *at this node*. Subnodes will still have the
        original dispatcher.

        BUG: This stacks weirdly with for_marker: if you parent() up one level
        and call .for_marker(), you'd expect to get the child dispatcher in the
        result, but instead you'll still have the parent. The right way to do
        this probably involves something like super() - it behaves like the
        parent, but still is the original.

        TODO Fix this? Or maybe it's ok? Or maybe it'll never come up?
        '''
        return DispatchOverlay(self, disp_target=DispatchSuper(disp, self.disp))

    def inner(self, *args, **kwargs):
        '''Unwrap self.marker by one layer and overlap.

        This is shorthand for self.for_marker(self.marker.marker)(*args,
        **kwargs). If self.marker is a Wrapper, this will call the dispatcher on
        its inner marker. If self.marker is not a wrapper, this will fail and
        your program will crash and it will be all your fault, you monster.
        '''
        return self.for_marker(self.marker.marker)(*args, **kwargs)

    def restrict(self, edge_names):
        return DispatchRestriction(self, edge_names)

# Wraps a graph of Marker values plus a common dispatcher
class DynamicDispatchGraph(DispatchGraph, vg.wrappers.GraphWrapper):
    '''DispatchGraph that wraps a graph of Markers.'''
    __slots__ = ('disp_target',)

    def __init__(self, graph, disp_target):
        self.graph = graph
        self.disp_target = disp_target

    def marker_graph(self):
        return self.graph

    @property
    def target(self):
        return self.graph.value

if True: # pragma: no cover
    # Untested, experimental feature.
    class _StaticDispatchGraph(vg.PlainGraphNode, DispatchGraph):
        '''
        This is an untested stub, not yet complete, but a note on how to make
        static dispatch graphs. Basically a StaticDispatchGraph is a dispatch
        graph where the dispatch is done once, beforehand, and the resulting
        functions are cached in the graph. An experiment on a list of ~3600
        SchemaObjs suggests that precomputing the dispatch like this makes
        undictify at least 30% faster. I suspect that for larger, more complex
        typegraphs the savings will be dramatically more.

        Also, it'd be even more awesome to inspect Wrappers and pre-dispatch on
        their internal types, too, so that .for_marker() would often not need to
        do any dispatch. Another option would be to have a structure that caches
        dispatches made, so that functions fetched via parent() and super()
        could be dispatched once and never hit again...
        '''
        __slots__ = ('value',)

        def _get_fn(self):
            return self.value[2]

    def _predispatch(target_and_disp):
        target, disp = target_and_disp[0], target_and_disp[1]
        return (target, disp, disp.dispatch(target))

    def _bake(dispgraph):
        return vg.map(dispgraph, _predispatch, cls=_StaticDispatchGraph)

# These two wrapper classes are the reason why we generally don't add new
# methods to GraphNode subclasses - helpful tools like ValueOverlay and
# EdgeRestriction need to be reimplemented as well.
class DispatchOverlay(vg.ValueOverlay, DispatchGraph):
    '''DispatchGraph that overlays another DispatchGraph with changed attrs.'''
    __slots__ = ()
    def __init__(self, graph, target=None, disp_target=None):
        if target is None:
            target = graph.target
        if disp_target is None:
            disp_target = graph.disp_target
        super(DispatchOverlay, self).__init__(graph, (target, disp_target))

    def marker_graph(self):
        return vg.ValueOverlay(self.graph.marker_graph(), self.target)


class DispatchRestriction(vg.EdgeRestriction, DispatchGraph):
    '''DispatchGraph that overlays another with restricted edges.'''
    __slots__ = ()
    def marker_graph(self):
        return vg.EdgeRestriction(self.graph.marker_graph(), self.edge_names)
