from collections import OrderedDict

import vertigo as vg

from .invalid import Invalid
from .base import Marker, graphize, traverse, mutate, clone
from .base import to_typegraph, aggregating_errors, IGNORE


class Schema(Marker):
    '''Abstract Marker for schema-structured objects.'''

    def of(self, **kwargs):
        children = {key:to_typegraph(val) for key, val in kwargs.items()}
        return vg.PlainGraphNode(self, **children)


def apply_schema(dispgraph, value, kw, default_nones=True):
    '''Apply a dispgraph to each element in value.

    This also handles error checking - if agg is not None, this will typecheck
    value and recurse to each element within agg.checking_sub().
    '''
    error_mode = kw.get('error_mode', IGNORE)
    def get(key):
        if default_nones:
            return value.get(key, None)
        return value[key]
    result = OrderedDict()
    if error_mode == IGNORE:
        for (key, subgraph) in dispgraph.edge_iter():
            result[key] = subgraph(get(key), **kw)
        return result
    with aggregating_errors(error_mode) as agg:
        if not isinstance(value, dict):
            msg = 'Expected a dict, got {} instead'.format(type(value))
            raise Invalid("type_error", msg, fatal=True)
        for key, subgraph in dispgraph.edge_iter():
            with agg.checking_sub(key):
                if key not in value and not default_nones:
                    raise Invalid("missing_attr")
                val = value.get(key, None)
                result[key] = subgraph(val, **kw)
        return result


@graphize.when(Schema)
def graphize_schema(dispgraph, value, **kw):
    edges = apply_schema(dispgraph, value, kw).items()
    if 'zipval' in dispgraph.extras:
        value = (value, dispgraph.extras.zipval)
    return vg.PlainGraphNode(value, edges)


@traverse.when(Schema)
def traverse_schema(dispgraph, value, **kw):
    apply_schema(dispgraph, value, kw, default_nones=False)


@clone.when(Schema)
def clone_schema(dispgraph, value, **kw):
    return apply_schema(dispgraph, value, kw)


@mutate.when(Schema)
def mutate_schema(dispgraph, value, **kw):
    error_mode = kw.get('error_mode', IGNORE)
    if error_mode != IGNORE and not isinstance(value, dict):
        msg = 'Expected a dict, got {} instead'.format(type(value))
        raise Invalid("type_error", msg, fatal=True)
    value.update(apply_schema(dispgraph, value, kw))
    return value
