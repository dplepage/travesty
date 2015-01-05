from .base import Marker, dictify, undictify

class Passthrough(Marker):
    '''A leaf value that can be dictified as is and needs no validation.

    >>> dictify(Passthrough(), 12)
    12
    >>> undictify(Passthrough(), {'x': [1, 2, 3]})
    {'x': [1, 2, 3]}
    '''

@dictify.when(Passthrough)
@undictify.when(Passthrough)
def passthrough(dispgraph, value, **kwargs):
    return value

