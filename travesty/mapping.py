import sys
if sys.version < '3': # pragma: no cover
    unicode_type = unicode
    bytes_type = str
else: # pragma: no cover
    bytes_type = bytes
    unicode_type = str
    basestring = str

import vertigo as vg

from .invalid import Invalid, InvalidAggregator
from .base import Marker, traverse, validate, dictify, undictify, to_typegraph
from .schema import Schema

class SchemaMapping(Schema):
    '''Marker for structured dicts.

    The children of this node in the typegraph indicate the types of the keyed
    attributes to traverse.

    >>> from collections import OrderedDict
    >>> from datetime import date
    >>> from . import Int, Date
    >>> G = vg.PlainGraphNode

    >>> bday = date(1985, 9, 16)
    >>> schema = G(SchemaMapping(), [("age",G(Int())), ("birthday",G(Date()))])
    >>> def mk(age, birthday):
    ...     return OrderedDict([('age', age), ('birthday', birthday)])
    >>> print(vg.ascii_tree(traverse(schema, mk(age=27, birthday=bday))))
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
def validate_mapping(dispgraph, value, **kwargs):
    if not isinstance(value, dict):
        raise Invalid("type_error", "Expected dict, got {}".format(type(value)))
    marker = dispgraph.marker
    error_agg = InvalidAggregator(autoraise = kwargs.get('fail_early', False))
    with error_agg.checking():
        dispgraph.super(SchemaMapping)(value, **kwargs)
    if marker.extra_field_policy in ['error', 'discard']:
        extra_keys = set(value.keys()) - set(dispgraph.key_iter())
        if extra_keys:
            error_agg.own_error(Invalid('unexpected_fields', keys=extra_keys))
    error_agg.raise_if_any()

@dictify.when(SchemaMapping)
def dictify_mapping(dispgraph, value, **kwargs):
    marker = dispgraph.marker
    result = dispgraph.super(SchemaMapping)(value, **kwargs)
    if marker.extra_field_policy == 'save':
        for key in set(value.keys()) - set(dispgraph.key_iter()):
            result[key] = value[key]
    return result


@undictify.when(SchemaMapping)
def undictify_mapping(dispgraph, value, **kwargs):
    marker = dispgraph.marker
    error_agg = InvalidAggregator(autoraise = kwargs.get('fail_early', False))
    with error_agg.checking():
        result = dispgraph.super(SchemaMapping)(value, **kwargs)
    extra_keys = set(value.keys()) - set(dispgraph.key_iter())
    if marker.extra_field_policy == 'error' and extra_keys:
        error_agg.own_error(Invalid('unexpected_fields', keys=extra_keys))
    elif marker.extra_field_policy == 'save':
        for key in extra_keys:
            result[key] = value[key]
    error_agg.raise_if_any()
    return result


class StrMapping(Marker):
    '''Marker for dicts with string keys and homogenous values.

    The sub child in the typegraph determines the types of the mapping's values.

    >>> from collections import OrderedDict
    >>> from vertigo import PlainGraphNode as G
    >>> from . import Int, Date, List
    >>> from datetime import date
    >>> StringToNumList = StrMapping().of(List().of(Int()))
    >>> example = OrderedDict([("foo",[1,2,3,4]), ("bar",[6,12,-4])])
    >>> print(vg.ascii_tree(traverse(StringToNumList, example), sort=True))
    root: OrderedDict([('foo', [1, 2, 3, 4]), ('bar', [6, 12, -4])])
      +--bar: [6, 12, -4]
      |  +--0: 6
      |  +--1: 12
      |  +--2: -4
      +--foo: [1, 2, 3, 4]
         +--0: 1
         +--1: 2
         +--2: 3
         +--3: 4
    >>> cstruct = dictify(StringToNumList, example)
    >>> cstruct == {'foo':[1,2,3,4], 'bar':[6,12,-4]}
    True
    >>> undictify(StringToNumList, cstruct) == example
    True
    >>> undictify(StringToNumList, None)
    Traceback (most recent call last):
    ...
    Invalid: type_error - Expected dict, got <type 'Nonetype'>
    >>> undictify(StringToNumList, {12:[1,2,3]})
    Traceback (most recent call last):
    ...
    Invalid: value_error/bad_keys - Bad keys - {'keys': [12]}
    >>> validate(StringToNumList, example)
    >>> validate(StringToNumList, {'foo':[1,"hi",3]})
    Traceback (most recent call last):
    ...
    Invalid: foo: [1: [type_error]]
    >>> validate(StringToNumList, {12:[1,2,3]})
    Traceback (most recent call last):
    ...
    Invalid: value_error/bad_keys - Bad keys - {'keys': [12]}
    >>> validate(StringToNumList, 12)
    Traceback (most recent call last):
    ...
    Invalid: type_error - Expected dict, got <type 'int'>

    >>> try:
    ...     undictify(StringToNumList, OrderedDict([
    ...         ('hello', None),
    ...     ]))
    ... except Invalid as e:
    ...     print(vg.ascii_tree(e.as_graph(), sort=True))
    root: []
      +--hello: [SingleInvalid('type_error',)]
    '''
    def of(self, sub):
        return vg.PlainGraphNode(self, sub = to_typegraph(sub))

@traverse.when(StrMapping)
def traverse_strmap(dispgraph, value, zipgraph=None, **kwargs):
    edges = []
    valgraph = dispgraph['sub']
    valzip = zipgraph['sub'] if zipgraph else None
    for key, val in value.items():
        edges.append((key, valgraph(val, valzip, **kwargs)))
    v = value
    if zipgraph:
        v = (v, zipgraph.value)
    return vg.PlainGraphNode(v, edges)

@undictify.when(StrMapping)
def undictify_strmap(dispgraph, value, **kwargs):
    if not isinstance(value, dict):
        raise Invalid("type_error", "Expected dict, got {}".format(type(value)))
    # If fail_early is True, then gather all errors from this and its
    # children. Otherwise, just raise the first error we encounter.
    error_agg = InvalidAggregator(autoraise = kwargs.get('fail_early', False))
    data = {}
    bad_keys = []
    for key, val in value.items():
        if not isinstance(key, basestring):
            bad_keys.append(key)
            continue
        with error_agg.checking_sub(key):
            val = dispgraph['sub'](val, **kwargs)
        data[key] = val
    if bad_keys:
        with error_agg.checking():
            raise Invalid("value_error/bad_keys", "Bad keys", keys=bad_keys)
    error_agg.raise_if_any()
    return data

@dictify.when(StrMapping)
def dictify_strmap(dispgraph, value, **kwargs):
    sub = dispgraph['sub']
    return {key:sub(val, **kwargs) for (key, val) in value.items()}

@validate.when(StrMapping)
def validate_strmap(dispgraph, value, **kwargs):
    if not isinstance(value, dict):
        raise Invalid("type_error", "Expected dict, got {}".format(type(value)))
    error_agg = InvalidAggregator(autoraise = kwargs.get('fail_early', False))
    bad_keys = []
    for key, val in value.items():
        if not isinstance(key, basestring):
            bad_keys.append(key)
            continue
        with error_agg.checking_sub(key):
            dispgraph['sub'](val, **kwargs)
    if bad_keys:
        with error_agg.checking():
            raise Invalid("value_error/bad_keys", "Bad keys", keys=bad_keys)
    error_agg.raise_if_any()

class UniMapping(Marker):
    '''Marker for dicts with homogenous keys and homogenous values.

    The key and val children in the typegraph determine the types of the
    mapping's keys and values, respectively.

    >>> from collections import OrderedDict
    >>> from vertigo import PlainGraphNode as G
    >>> from . import Int, Date, List
    >>> from datetime import date
    >>> DateToNumList = G.build(dict(
    ...     _self=UniMapping(),
    ...     key=Date(),
    ...     val=dict(_self=List(), sub=Int()))
    ... )
    >>> d1, d2 = date(1985, 9, 16), date(1980, 3, 17)
    >>> example = OrderedDict([(d1,[1,2,3,4]), (d2,[6,12,-4])])
    >>> print(vg.ascii_tree(traverse(DateToNumList, example), sort=True))
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
    >>> cstruct = dictify(DateToNumList, example)
    >>> cstruct == {u'1985-09-16':[1,2,3,4], '1980-03-17':[6,12,-4]}
    True
    >>> undictify(DateToNumList, cstruct) == example
    True
    >>> undictify(DateToNumList, None)
    Traceback (most recent call last):
    ...
    Invalid: type_error - Expected dict, got <type 'Nonetype'>
    >>> validate(DateToNumList, example)
    >>> validate(DateToNumList, {"not a date":[1,2,3]})
    Traceback (most recent call last):
    ...
    Invalid: key_0: [type_error]
    >>> validate(DateToNumList, {d1:[1,"hi",3]})
    Traceback (most recent call last):
    ...
    Invalid: value_0: [1: [type_error]]
    >>> validate(DateToNumList, 12)
    Traceback (most recent call last):
    ...
    Invalid: type_error - Expected dict, got <type 'int'>

    >>> try:
    ...     undictify(DateToNumList, OrderedDict([
    ...         ('1985-09-16', [1, 'hi']),
    ...         ('hello', None),
    ...     ]))
    ... except Invalid as e:
    ...     print(vg.ascii_tree(e.as_graph(), sort=True))
    root: []
      +--key_1: [SingleInvalid('bad_format',)]
      +--value_1: [SingleInvalid('type_error',)]

    Caveat: Note that if the value passed in is not an OrderedDict, then there's
    no guarantee of the numerical order of the errors or of the traversal -
    '''
    def of(self, key, val):
        key, val = to_typegraph(key), to_typegraph(val)
        return vg.PlainGraphNode(self, key=key, val=val)

@traverse.when(UniMapping)
def traverse_unimap(dispgraph, value, zipgraph=None, **kwargs):
    edges = []
    keygraph = dispgraph['key']
    valgraph = dispgraph['val']
    keyzip = zipgraph['key'] if zipgraph else None
    valzip = zipgraph['val'] if zipgraph else None
    for i, (key, val) in enumerate(value.items()):
        edges.append(('key_{}'.format(i), keygraph(key, keyzip, **kwargs)))
        edges.append(('value_{}'.format(i), valgraph(val, valzip, **kwargs)))
    v = value
    if zipgraph:
        v = (v, zipgraph.value)
    return vg.PlainGraphNode(v, edges)


@undictify.when(UniMapping)
def undictify_unimap(dispgraph, value, **kwargs):
    if not isinstance(value, dict):
        raise Invalid("type_error", "Expected dict, got {}".format(type(value)))
    # If fail_early is True, then gather all errors from this and its
    # children. Otherwise, just raise the first error we encounter.
    error_agg = InvalidAggregator(autoraise = kwargs.get('fail_early', False))
    data = {}
    for i, (key, val) in enumerate(value.items()):
        with error_agg.checking_sub('key_{}'.format(i)):
            key = dispgraph['key'](key, **kwargs)
        with error_agg.checking_sub('value_{}'.format(i)):
            val = dispgraph['val'](val, **kwargs)
        data[key] = val
    error_agg.raise_if_any()
    return data

@dictify.when(UniMapping)
def dictify_unimap(dispgraph, value, **kwargs):
    kdfy = lambda x: dispgraph['key'](x, **kwargs)
    vdfy = lambda x: dispgraph['val'](x, **kwargs)
    return {kdfy(key):vdfy(val) for (key, val) in value.items()}

@validate.when(UniMapping)
def validate_unimap(dispgraph, value, **kwargs):
    if not isinstance(value, dict):
        raise Invalid("type_error", "Expected dict, got {}".format(type(value)))
    error_agg = InvalidAggregator(autoraise = kwargs.get('fail_early', False))
    for i, (key, val) in enumerate(value.items()):
        with error_agg.checking_sub('key_{}'.format(i)):
            dispgraph['key'](key, **kwargs)
        with error_agg.checking_sub('value_{}'.format(i)):
            dispgraph['val'](val, **kwargs)
    error_agg.raise_if_any()



if __name__ == '__main__': # pragma: no cover
    import doctest
    doctest.testmod()
