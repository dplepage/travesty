import vertigo as vg

from .invalid import Invalid, InvalidAggregator
from .base import Marker, traverse, validate, dictify, undictify, to_typegraph

class Schema(Marker):
    '''Abstract Marker for schema-structured objects.'''

    def of(self, **kwargs):
        children = {key:to_typegraph(val) for key, val in kwargs.items()}
        return vg.PlainGraphNode(self, **children)

_foo = traverse

@traverse.when(Schema)
def traverse_schema(dispgraph, value, zipgraph=None, **kwargs):
    edges = []
    for key, subgraph in dispgraph.edge_iter():
        subzip = zipgraph[key] if zipgraph else None
        edges.append((key, subgraph(value[key], subzip, **kwargs)))
    v = value
    if zipgraph:
        v = (v, zipgraph.value)
    return vg.PlainGraphNode(v, edges)

@validate.when(Schema)
def validate_schema(dispgraph, value, **kwargs):
    error_agg = InvalidAggregator(autoraise = kwargs.get('fail_early', False))
    for key, subgraph in dispgraph.edge_iter():
        with error_agg.checking_sub(key):
            if key not in value:
                raise Invalid("missing_key", "Missing key {}".format(key))
            subgraph(value[key], **kwargs)
    error_agg.raise_if_any()

@dictify.when(Schema)
def dictify_schema(dispgraph, value, **kwargs):
    result = {}
    for key, subgraph in dispgraph.edge_iter():
        result[key] = subgraph(value[key], **kwargs)
    return result

@undictify.when(Schema)
def undictify_schema(dispgraph, value, **kwargs):
    if not isinstance(value, dict):
        raise Invalid('type_error', 'Expected a dict, got {} instead'.format(type(value)))
    # If fail_early is True, then gather all errors from this and its
    # children. Otherwise, just raise the first error we encounter.
    error_agg = InvalidAggregator(autoraise = kwargs.get('fail_early', False))
    result = {}
    for key, subgraph in dispgraph.edge_iter():
        with error_agg.checking_sub(key):
            val = value.get(key, None)
            result[key] = subgraph(val, **kwargs)
    error_agg.raise_if_any()
    return result
