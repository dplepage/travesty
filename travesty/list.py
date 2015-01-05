import vertigo as vg

from .base import Marker, traverse, validate, dictify, undictify
from .base import to_typegraph
from .invalid import Invalid, InvalidAggregator

class List(Marker):
    '''Marker for homogenous lists.

    The 'sub' child in the typegraph indicates the marker for all items in the
    list.

    For example:

    >>> from travesty import Int, Optional
    >>> l = List().of(Int())

    >>> print(vg.ascii_tree(traverse(l, [1, 2, 3]), sort=True))
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

@traverse.when(List)
def traverse_list(dispgraph, value, zipgraph=None, **kwargs):
    edges = []
    subzip = zipgraph['sub'] if zipgraph else None
    for i,val in enumerate(value):
        key = str(i)
        node = dispgraph['sub'](val, zipgraph=subzip, **kwargs)
        edges.append((key,node))
    v = value
    if zipgraph:
        v = (v, zipgraph.value)
    return vg.PlainGraphNode(v, edges)

@validate.when(List)
def validate_list(dispgraph, value, **kwargs):
    error_agg = InvalidAggregator(autoraise = kwargs.get('fail_early', False))
    try:
        iterator = iter(value)
    except TypeError: # item isn't iterable!
        raise Invalid("type_error", "Value is not iterable")
    for i, item in enumerate(iterator):
        with error_agg.checking_sub(str(i)):
            dispgraph['sub'](item, **kwargs)
    error_agg.raise_if_any()

@undictify.when(List)
def undictify_list(dispgraph, value, **kwargs):
    # If _full_errors is True, then gather all errors from this and its
    # children. Otherwise, just raise the first error we encounter.
    error_agg = InvalidAggregator(autoraise = kwargs.get('fail_early', False))
    try:
        iterator = iter(value)
    except TypeError: # item isn't iterable!
        raise Invalid("type_error", "Value is not iterable")
    result = []
    for i, item in enumerate(iterator):
        with error_agg.checking_sub(str(i)):
            result.append(dispgraph['sub'](item, **kwargs))
    error_agg.raise_if_any()
    return result

@dictify.when(List)
def dictify_list(dispgraph, value, **kwargs):
    return [dispgraph['sub'](x, **kwargs) for x in value]

if __name__ == '__main__': # pragma: no cover
    import doctest
    doctest.testmod()
