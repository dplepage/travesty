import vertigo as vg

from . import Wrapper, graphize, clone, traverse

class Optional(Wrapper):
    '''Wrapper that indicates the value could be None.

    >>> import travesty as tv

    None fails validation, won't always undictify, etc.

    >>> tv.validate(tv.Int(), None)
    Traceback (most recent call last):
        ...
    Invalid: type_error
    >>> tv.undictify(tv.List().of(tv.Int()), None)
    Traceback (most recent call last):
        ...
    Invalid: type_error

    Wrapping it in Optional fixes this:

    >>> tv.validate(Optional.wrap(tv.Int()), None)
    >>> tv.undictify(Optional.wrap(tv.Int()), None) is None
    True

    '''
    pass

@graphize.when(Optional)
def graphize_optional(dispgraph, value, **kw):
    if value is None:
        if 'zipval' in dispgraph.extras:
            return vg.PlainGraphNode((None, dispgraph.extras.zipval))
        return vg.PlainGraphNode(None)
    opt = dispgraph.marker
    return dispgraph.for_marker(opt.marker)(value, **kw)


@clone.when(Optional)
def clone_optional(dispgraph, value, **kw):
    if value is None:
        return None
    opt = dispgraph.marker
    return dispgraph.for_marker(opt.marker)(value, **kw)


@traverse.when(Optional)
def traverse_optional(dispgraph, value, **kw):
    if value is None:
        return
    opt = dispgraph.marker
    dispgraph.for_marker(opt.marker)(value, **kw)
