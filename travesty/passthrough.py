from .base import Leaf

class Passthrough(Leaf):
    '''An explicitly ignored leaf value.

    All the various travesty-defined dispatchers will pass values through
    unchanged:

    >>> import travesty as tv
    >>> tv.dictify(Passthrough(), 12)
    12
    >>> tv.undictify(Passthrough(), {'x': [1, 2, 3]})
    {'x': [1, 2, 3]}
    >>> tv.validate(Passthrough(), Exception("This could be any object"))
    >>>
    '''
    # No code needed - Leaf does this already. Passthrough is just here to be
    # more explicit.
