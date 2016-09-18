import vertigo as vg

from .base import Marker, graphize, traverse, clone, mutate
from .base import to_typegraph, aggregating_errors, IGNORE
from .invalid import Invalid

class List(Marker):
    '''Marker for homogenous lists.

    The 'sub' child in the typegraph indicates the marker for all items in the
    list.

    For example:

    >>> from travesty import Int, Optional, dictify, undictify, validate
    >>> l = List().of(Int())

    >>> print(vg.ascii_tree(graphize(l, [1, 2, 3]), sort=True))
    root: [1, 2, 3]
      +--0: 1
      +--1: 2
      +--2: 3

    >>> undictify(l, [1, 4, 5])
    [1, 4, 5]
    >>> dictify(l, [1, 2, 3])
    [1, 2, 3]

    >>> validate(l, [1, 2, 3])
    >>> try:
    ...     validate(l, [1, None, 'hi'])
    ... except Invalid as e:
    ...     print(vg.ascii_tree(e.as_graph(), sort=True))
    root: []
      +--1: [SingleInvalid('type_error',)]
      +--2: [SingleInvalid('type_error',)]
    >>> l = List().of(Optional.wrap(Int()))
    >>> validate(l, [1, None, 'hi'])
    Traceback (most recent call last):
    ...
    Invalid: 2: [type_error]
    >>> validate(l, 12)
    Traceback (most recent call last):
    ...
    Invalid: type_error
    '''
    def of(self, sub):
        return vg.PlainGraphNode(self, sub=to_typegraph(sub))


def apply_list(dispgraph, value, kw):
    '''Apply a dispgraph to each element in value.

    This also handles error checking - if agg is not None, this will typecheck
    value and recurse to each element within agg.checking_sub().
    '''
    error_mode = kw.get('error_mode', IGNORE)
    if error_mode == IGNORE:
        return [dispgraph['sub'](v, **kw) for v in value]
    with aggregating_errors(error_mode) as agg:
        if not isinstance(value, (list, tuple)):
            msg = "Expected list, got {}".format(type(value).__name__)
            raise Invalid("type_error", msg, fatal=True)
        result = []
        for i, v in enumerate(value):
            with agg.checking_sub(str(i)):
                result.append(dispgraph['sub'](v, **kw))
        return result


@graphize.when(List)
def graphize_list(dispgraph, value, **kw):
    edges = apply_list(dispgraph, value, kw)
    edges = ((str(i), v) for (i,v) in enumerate(edges))
    if 'zipval' in dispgraph.extras:
        value = (value, dispgraph.extras.zipval)
    return vg.PlainGraphNode(value, edges)


@traverse.when(List)
def traverse_list(dispgraph, value, **kw):
    apply_list(dispgraph, value, kw)


@mutate.when(List)
def mutate_list(dispgraph, value, **kw):
    value[:] = apply_list(dispgraph, value, kw)
    return value


@clone.when(List)
def clone_list(dispgraph, value, **kw):
    return apply_list(dispgraph, value, kw)


if __name__ == '__main__': # pragma: no cover
    import doctest
    doctest.testmod()
