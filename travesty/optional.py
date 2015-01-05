import vertigo as vg

from . import Wrapper, traverse, dictify, undictify, validate

class Optional(Wrapper):
    '''Wrapper that indicates the value could be None.

    >>> from . import Int, List

    None fails validation, won't always undictify, etc.

    >>> validate(Int(), None)
    Traceback (most recent call last):
        ...
    Invalid: type_error
    >>> undictify(List().of(Int()), None)
    Traceback (most recent call last):
        ...
    Invalid: type_error

    Wrapping it in Optional fixes this:

    >>> validate(Optional.wrap(Int()), None)
    >>> undictify(Optional.wrap(Int()), None) is None
    True

    '''
    pass

@traverse.when(Optional)
def traverse_optional(dispgraph, value, zipgraph=None, **kwargs):
    if value is None:
        if zipgraph:
            return vg.PlainGraphNode((value, zipgraph.value))
        return vg.PlainGraphNode(value)
    opt = dispgraph.marker
    return dispgraph.for_marker(opt.marker)(value, zipgraph=zipgraph, **kwargs)


@dictify.when(Optional)
@undictify.when(Optional)
def dfy_undfy_optional(dispgraph, value, **kwargs):
    if value is None:
        return None
    opt = dispgraph.marker
    return dispgraph.for_marker(opt.marker)(value, **kwargs)


@validate.when(Optional)
def validate_optional(dispgraph, value, **kwargs):
    if value is None:
        return
    opt = dispgraph.marker
    dispgraph.for_marker(opt.marker)(value, **kwargs)
