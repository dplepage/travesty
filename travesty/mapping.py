import sys
from collections import OrderedDict
if sys.version >= '3': # pragma: no cover
    basestring = str

import vertigo as vg

from .invalid import Invalid
from .base import graphize, traverse, clone, mutate, validate
from .base import Marker, IGNORE, to_typegraph, aggregating_errors
from .schema import Schema

class SchemaMapping(Schema):
    '''Marker for structured dicts.

    The children of this node in the typegraph indicate the types of the keyed
    attributes to traverse.

    >>> from datetime import date
    >>> from . import Int, Date, undictify, dictify
    >>> G = vg.PlainGraphNode

    >>> bday = date(1985, 9, 16)
    >>> schema = G(SchemaMapping(), [("age",G(Int())), ("birthday",G(Date()))])
    >>> def mk(age, birthday):
    ...     return OrderedDict([('age', age), ('birthday', birthday)])
    >>> print(vg.ascii_tree(graphize(schema, mk(age=27, birthday=bday))))
    root: OrderedDict([('age', 27), ('birthday', datetime.date(1985, 9, 16))])
      +--age: 27
      +--birthday: datetime.date(1985, 9, 16)

    >>> validate(schema, mk(age=27, birthday=bday))
    >>> validate(schema, mk(age=27.1, birthday="not a date"))
    Traceback (most recent call last):
    ...
    Invalid: age: [type_error], birthday: [type_error]

    >>> cstruct = dictify(schema, mk(age=27, birthday=bday))
    >>> cstruct == mk(age=27, birthday=u'1985-09-16')
    True
    >>> undictify(schema, cstruct) == mk(age=27, birthday=bday)
    True

    The 'extra_field_policy' flag should be 'save', 'discard', or 'error'. This
    controls what happens on undictifiance when unexpected fields are present.

    'save': un/dictify preserves extra keys; validate ignores them

    >>> schema = G.build(dict(_self=SchemaMapping('save'), age=Int()))
    >>> v = undictify(schema, {'age':27, 'color':'blue'})
    >>> v == {'age': 27, 'color': 'blue'}
    True
    >>> validate(schema, v)
    >>> v = dictify(schema, {'age':27, 'color':'blue'})
    >>> v == {'age': 27, 'color': 'blue'}
    True

    'discard': un/dictify discards extra keys; validate complains about them

    >>> schema = G.build(dict(_self=SchemaMapping('discard'), age=Int()))
    >>> v = undictify(schema, {'age':27, 'color':'blue'})
    >>> v == {'age': 27}
    True
    >>> validate(schema, v)
    >>> validate(schema, {'age':27, 'color':'blue'})
    Traceback (most recent call last):
    ...
    Invalid: unexpected_fields - {'keys': set(['color'])}
    >>> v = dictify(schema, {'age':27, 'color':'blue'})
    >>> v == {'age': 27}
    True

    'error': undictify and validate complain; dictify discards

    >>> schema = G.build(dict(_self=SchemaMapping('error'), age=Int()))
    >>> v = undictify(schema, {'age':27, 'color':'blue'})
    Traceback (most recent call last):
    ...
    Invalid: unexpected_fields - {'keys': set(['color'])}
    >>> validate(schema, {'age':27, 'color':'blue'})
    Traceback (most recent call last):
    ...
    Invalid: unexpected_fields - {'keys': set(['color'])}
    >>> v = dictify(schema, {'age':27, 'color':'blue'})
    >>> v == {'age': 27}
    True

    >>> validate(schema, 12)
    Traceback (most recent call last):
    ...
    Invalid: type_error - Expected dict, got <type 'int'>
    '''
    def __init__(self, extra_field_policy="discard"):
        super(SchemaMapping, self).__init__()
        self.extra_field_policy=extra_field_policy


@validate.when(SchemaMapping)
def validate_mapping(dispgraph, value, **kw):
    error_mode = kw.get('error_mode', IGNORE)
    marker = dispgraph.marker
    with aggregating_errors(error_mode) as agg:
        dispgraph.super(SchemaMapping)(value, **kw)
        if agg and marker.extra_field_policy in ['discard', 'error']:
            extra_keys = set(value.keys()) - set(dispgraph.key_iter())
            if extra_keys:
                agg.own_error(Invalid('unexpected_fields', keys=extra_keys))


@clone.when(SchemaMapping)
def clone_mapping(dispgraph, value, **kw):
    error_mode = kw.get('error_mode', IGNORE)
    marker = dispgraph.marker
    with aggregating_errors(error_mode) as agg:
        result = dispgraph.super(SchemaMapping)(value, **kw)
        extra_keys = set(value.keys()) - set(dispgraph.key_iter())
        if extra_keys:
            if agg and marker.extra_field_policy == 'error':
                raise Invalid('unexpected_fields', keys=extra_keys)
            if marker.extra_field_policy == 'save':
                for key in extra_keys:
                    result[key] = value[key]
    return result


@mutate.when(SchemaMapping)
def mutate_mapping(dispgraph, value, **kw):
    newval = clone_mapping(dispgraph, value, **kw)
    value.update(newval)
    return value


class StrMapping(Marker):
    '''Marker for dicts with string keys and homogenous values.

    The sub child in the typegraph determines the types of the mapping's values.

    For example, here's a type that maps strings to dates:

    >>> from datetime import date, timedelta
    >>> from collections import OrderedDict
    >>> import travesty as tv
    >>> DateMap = StrMapping().of(tv.Date())
    >>> d1, d2 = date(1985, 9, 16), date(1980, 3, 17)
    >>> example = OrderedDict([
    ...     ("foo", d1),
    ...     ("bar", d2)])
    >>> print(vg.ascii_tree(graphize(DateMap, example), sort=True))
    root: OrderedDict([('foo', datetime.date(1985, 9, 16)), ('bar', datetime.date(1980, 3, 17))])
      +--bar: datetime.date(1980, 3, 17)
      +--foo: datetime.date(1985, 9, 16)

    Dictifying it will map each key to its dictified value:

    >>> cstruct = tv.dictify(DateMap, example)
    >>> cstruct == {'foo':'1985-09-16', 'bar':'1980-03-17'}
    True
    >>> tv.undictify(DateMap, cstruct) == dict(example)
    True

    The validators expect a dict, and will complain if non-string keys are
    present:

    >>> tv.undictify(DateMap, None)
    Traceback (most recent call last):
    ...
    Invalid: type_error - Expected dict, got <type 'Nonetype'>
    >>> tv.undictify(DateMap, {12:d1})
    Traceback (most recent call last):
    ...
    Invalid: value_error/bad_keys - Bad keys - {'keys': [12]}
    >>> tv.validate(DateMap, example)
    >>> tv.validate(DateMap, {'foo':'not a date'})
    Traceback (most recent call last):
    ...
    Invalid: foo: [type_error]
    >>> tv.validate(DateMap, {12:d1})
    Traceback (most recent call last):
    ...
    Invalid: value_error/bad_keys - Bad keys - {'keys': [12]}

    Mutate will leave the keys unchanged:

    >>> Str2Str = StrMapping().of(tv.String())
    >>> double = tv.mutate.sub()
    >>> @double.when(tv.String)
    ... def double_string(dispgraph, value, **kw): return value*2
    ...
    >>> x = dict(a='b', c='d')
    >>> double(Str2Str, x) == dict(a='bb', c='dd')
    True
    '''
    def of(self, sub):
        return vg.PlainGraphNode(self, sub = to_typegraph(sub))

def apply_strmap(dispgraph, value, kw):
    '''Apply a dispgraph to each element in value.

    This also handles error checking - if agg is not None, this will typecheck
    value and recurse to each element within agg.checking_sub().
    '''
    error_mode = kw.get('error_mode', IGNORE)
    vfn = lambda x: dispgraph['sub'](x, **kw)
    if error_mode == IGNORE:
        return {key:vfn(val) for (key, val) in value.items()}
    if not isinstance(value, dict):
        msg = "Expected dict, got {}".format(type(value))
        raise Invalid("type_error", msg, fatal=True)
    result = OrderedDict()
    bad_keys = []
    with aggregating_errors(error_mode) as agg:
        for key, val in value.items():
            if not isinstance(key, basestring):
                bad_keys.append(key)
                continue
            with agg.checking_sub(key):
                result[key] = vfn(val)
        if bad_keys:
            raise Invalid("value_error/bad_keys", "Bad keys", keys=bad_keys)
    return result


@graphize.when(StrMapping)
def graphize_strmap(dispgraph, value, **kw):
    edges = apply_strmap(dispgraph, value, kw).items()
    if 'zipval' in dispgraph.extras:
        value = (value, dispgraph.extras.zipval)
    return vg.PlainGraphNode(value, edges)


@clone.when(StrMapping)
def clone_strmap(dispgraph, value, **kw):
    return apply_strmap(dispgraph, value, kw)


@mutate.when(StrMapping)
def mutate_strmap(dispgraph, value, **kw):
    value.update(apply_strmap(dispgraph, value, kw))
    return value


@traverse.when(StrMapping)
def traverse_strmap(dispgraph, value, **kw):
    apply_strmap(dispgraph, value, kw)


class UniMapping(Marker):
    '''Marker for dicts with homogenous keys and homogenous values.

    The key and val children in the typegraph determine the types of the
    mapping's keys and values, respectively.

    >>> from collections import OrderedDict
    >>> import travesty as tv
    >>> from datetime import date, timedelta
    >>> DateToNumList = UniMapping().of(
    ...     key=tv.Date(),
    ...     val=tv.List().of(tv.Int()),
    ... )
    >>> d1, d2 = date(1985, 9, 16), date(1980, 3, 17)
    >>> example = OrderedDict([(d1,[1,2,3,4]), (d2,[6,12,-4])])

    Graphize will label the keys `key_i` and the values `value_i`:

    >>> print(vg.ascii_tree(tv.graphize(DateToNumList, example), sort=True))
    root: OrderedDict([(datetime.date(1985, 9, 16), [1, 2, 3, 4]), (datetime.date(1980, 3, 17), [6, 12, -4])])
      +--key_0: datetime.date(1985, 9, 16)
      +--key_1: datetime.date(1980, 3, 17)
      +--value_0: [1, 2, 3, 4]
      |  +--0: 1
      |  +--1: 2
      |  +--2: 3
      |  +--3: 4
      +--value_1: [6, 12, -4]
         +--0: 6
         +--1: 12
         +--2: -4

    Dictifying will map each dictified key to its dictified value:

    >>> cstruct = tv.dictify(DateToNumList, example)
    >>> cstruct == {u'1985-09-16':[1,2,3,4], '1980-03-17':[6,12,-4]}
    True
    >>> tv.undictify(DateToNumList, cstruct) == example
    True

    Validation expects a dictionary:

    >>> tv.validate(DateToNumList, example)
    >>> tv.validate(DateToNumList, 12)
    Traceback (most recent call last):
    ...
    Invalid: type_error - Expected dict, got <type 'int'>

    Exceptions will also use `key_i`/`value_i` to indicate sub-problems:

    >>> try:
    ...     tv.undictify(DateToNumList, OrderedDict([
    ...         ('1985-09-16', None),
    ...         ('hello', [1, 'hi']),
    ...     ]))
    ... except Invalid as e:
    ...     print(vg.ascii_tree(e.as_graph(), sort=True))
    root: []
      +--key_1: [SingleInvalid('bad_format',)]
      +--value_0: [SingleInvalid('type_error',)]

    Caveat: Note that if the value passed in is not an OrderedDict, then there's
    no guarantee of the numerical order of the errors or of the graphize result.
    There's not really a good way to handle this; use OrderedDict if you need
    to be able to map problems back to their specific keys.

    Mutate will replace keys if they change:

    >>> one_day_more = tv.mutate.sub()
    >>> @one_day_more.when(tv.Date)
    ... def tomorrow(dispgraph, value, **kw):
    ...     return value + timedelta(days=1)
    ...
    >>> _ = one_day_more(DateToNumList, example)
    >>> example[date(1985, 9, 17)]
    [1, 2, 3, 4]

    '''
    def of(self, key, val):
        key, val = to_typegraph(key), to_typegraph(val)
        return vg.PlainGraphNode(self, key=key, val=val)


def apply_unimap(dispgraph, value, kw):
    '''Apply a dispgraph to each element in value.

    This also handles error checking - if agg is not None, this will typecheck
    value and recurse to each element within agg.checking_sub().
    '''
    error_mode = kw.get('error_mode', IGNORE)
    kfn = lambda x: dispgraph['key'](x, **kw)
    vfn = lambda x: dispgraph['val'](x, **kw)
    result = OrderedDict()
    if error_mode == IGNORE:
        for (key, val) in value.items():
            result[kfn(key)] = vfn(val)
        return result
    if not isinstance(value, dict):
        msg = "Expected dict, got {}".format(type(value))
        raise Invalid("type_error", msg, fatal=True)
    with aggregating_errors(error_mode) as agg:
        for i, (key, val) in enumerate(value.items()):
            with agg.checking_sub('key_{}'.format(i)):
                key = kfn(key)
            with agg.checking_sub('value_{}'.format(i)):
                val = vfn(val)
            result[key] = val
    return result

@graphize.when(UniMapping)
def graphize_unimap(dispgraph, value, **kw):
    result = apply_unimap(dispgraph, value, kw)
    edges = []
    for i, (key, val) in enumerate(result.items()):
        edges.append(('key_{}'.format(i), key))
        edges.append(('value_{}'.format(i), val))
    if 'zipval' in dispgraph.extras:
        value = (value, dispgraph.extras.zipval)
    return vg.PlainGraphNode(value, edges)


@clone.when(UniMapping)
def clone_unimap(dispgraph, value, **kw):
    return apply_unimap(dispgraph, value, kw)


@mutate.when(UniMapping)
def mutate_unimap(dispgraph, value, **kw):
    new_values = apply_unimap(dispgraph, value, kw)
    # Clear in case the keys were mutated
    value.clear()
    value.update(new_values)
    return value


@traverse.when(UniMapping)
def traverse_unimap(dispgraph, value, **kw):
    apply_unimap(dispgraph, value, kw)
