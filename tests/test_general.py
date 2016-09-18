from collections import OrderedDict

import vertigo as vg

from travesty import Int, List, String, SchemaMapping, UniMapping, Wrapper
from travesty import StrMapping
from travesty import Marker, unwrap, core_marker, to_typegraph, make_dispatcher
from travesty import dictify, undictify, graphize, validate, Invalid, Optional
from travesty.dispatch_graph import DispatchGraph

from helpers import expecting, match_asc

def test_to_typegraph():
    with expecting(NotImplementedError):
        to_typegraph(12)
    with expecting(NotImplementedError):
        to_typegraph(int)

def test_wrapper():
    class Foo(Wrapper):
        pass

    class Bar(Wrapper):
        pass

    i = Int()
    bi = Bar(i)
    fbi = Foo(bi)
    assert undictify(fbi, 12) == 12
    assert unwrap(bi) is unwrap(fbi) is i
    assert unwrap(fbi, Foo) is fbi
    assert unwrap(fbi, Bar) is bi
    assert unwrap(bi, Foo) is None
    assert unwrap(fbi, Int) is i
    assert unwrap(fbi, String) is None
    assert core_marker(fbi) is i

    class Annotated(Wrapper):
        def __init__(self, marker, kw={}, **kwargs):
            kwargs.update(kw)
            self.kw = kwargs
            super(Annotated, self).__init__(marker)

    addfoo = Annotated.factory(foo=12)
    ai = addfoo(Int())
    fabi = Foo(addfoo(Bar(Int())))
    assert ai.kw['foo'] == 12
    assert unwrap(fabi, Annotated).kw['foo'] == 12


def test_invalid():
    i = Invalid()
    assert i.id_string() == "<no message>"

def test_zipgraph():
    g = List().of(sub=Int())
    g2 = vg.from_dict(dict(_self="A List", sub="Some Element"))
    g3 = graphize(g, [1,2,3], extras_graphs={'zipval':g2})
    match_asc(g3, '''
        root: ([1, 2, 3], 'A List')
          +--0: (1, 'Some Element')
          +--1: (2, 'Some Element')
          +--2: (3, 'Some Element')
    ''')

    g = Optional.wrap(UniMapping().of(String(), Int()))
    g2 = vg.from_dict(dict(_self="The map", key="A Key", val="A Value"))
    val = OrderedDict([('foo', 12), ('bar', 14)])
    g3 = graphize(g, val, extras_graphs={'zipval':g2})
    match_asc(g3, '''
        root: (OrderedDict([('foo', 12), ('bar', 14)]), 'The map')
          +--key_0: ('foo', 'A Key')
          +--key_1: ('bar', 'A Key')
          +--value_0: (12, 'A Value')
          +--value_1: (14, 'A Value')
    ''')
    g3 = graphize(g, None, extras_graphs={'zipval':g2})
    match_asc(g3, '''
        root: (None, 'The map')
    ''')

    g = Optional.wrap(StrMapping().of(Int()))
    g2 = vg.from_dict(dict(_self="The map", sub="A Value"))
    val = OrderedDict([('foo', 12), ('bar', 14)])
    g3 = graphize(g, val, extras_graphs={'zipval':g2})
    match_asc(g3, '''
        root: (OrderedDict([('foo', 12), ('bar', 14)]), 'The map')
          +--bar: (14, 'A Value')
          +--foo: (12, 'A Value')
    ''')
    g3 = graphize(g, None, extras_graphs={'zipval':g2})
    match_asc(g3, '''
        root: (None, 'The map')
    ''')

def test_extras_graphs():
    show_extras = dictify.sub()
    @show_extras.when(Int)
    def show_extras_int(dispgraph, value, **kw):
        return (dispgraph.extras.foo, dispgraph.extras.get('bar'))
    x = show_extras(Int(), 1, extras_graphs=dict(foo=vg.PlainGraphNode(1)))
    assert x == (1, None)
    g = dict(
        foo=vg.from_flat({
            'sub': 'fooval',
        }),
        bar = vg.from_flat({
            'sub': 'barval',
        }))
    x = show_extras(List().of(Int()), [1,2,3], extras_graphs=g)
    assert x == [('fooval', 'barval')]*3
    # foo is required, so fail without it:
    with expecting(AttributeError):
        x = show_extras(List().of(Int()), [1,2,3])

def test_base_validate():
    validate(Marker(), 12)

def test_unimplemented():
    with expecting(NotImplementedError):
        dictify(Marker(), None)
    with expecting(NotImplementedError):
        DispatchGraph().marker_graph()

def test_manipulation():
    class Foo(Wrapper): pass
    class Bar(Foo): pass
    d1 = make_dispatcher()
    d2 = d1.sub()
    @d1.when(Foo)
    def d1_foo(dispgraph):
        return "d1_foo"
    @d1.when(Bar)
    def d1_bar(dispgraph):
        return "d1_bar " + dispgraph.super(Bar)()
    @d2.when(Foo)
    def d2_foo(dispgraph):
        return "d2_foo " + dispgraph.parent(d2)()
    @d2.when(Bar)
    def d2_bar(dispgraph):
        return ["d2_bar "+dispgraph.parent(d2)(), "d2_bar "+dispgraph.super(Bar)()]

    typegraph = Bar.wrap(SchemaMapping().of(x=Int(), y=Int()))
    dispgraph = d2._mk_graph(typegraph)
    parentgraph = dispgraph.parent(d2)
    supergraph = dispgraph.super(Bar)
    rgraph = dispgraph.restrict(['x'])

    match_asc(dispgraph.marker_graph(), '''
        root: <Bar(SchemaMapping)>
          +--x: <Int>
          +--y: <Int>
    ''')
    assert dispgraph.disp is d2
    assert dispgraph.value == (typegraph.value, d2, {}), dispgraph.value

    match_asc(parentgraph.marker_graph(), '''
        root: <Bar(SchemaMapping)>
          +--x: <Int>
          +--y: <Int>
    ''')
    assert parentgraph.disp is d2
    assert parentgraph.value[0] is typegraph.value
    assert parentgraph.value[1].disp is d2 # it's a DispatchSuper

    match_asc(supergraph.marker_graph(), '''
        root: SuperMarker(key={}, val=<Bar(SchemaMapping)>)
          +--x: <Int>
          +--y: <Int>
    '''.format(Bar))
    assert supergraph.disp is d2

    match_asc(rgraph.marker_graph(), '''
        root: <Bar(SchemaMapping)>
          +--x: <Int>
    ''')
    assert rgraph.disp is d2

    with expecting(KeyError):
        rgraph['y']


def test_super():
    s = undictify.sub()
    class Foo(Marker):
        def __init__(self, x):
            self.x = x
    class Bar(Foo):
        def __init__(self, x, y):
            self.x, self.y = x, y
    class Baz(Bar):
        def __init__(self, x, y, z):
            self.x, self.y, self.z = x, y, z
    @s.when(Foo)
    def udf_foo(dispgraph, value, **kwargs):
        return dict(x=dispgraph.marker.x)
    @s.when(Bar)
    def udf_bar(dispgraph, value, **kwargs):
        d = dispgraph.super(Bar)(value, **kwargs)
        d['y'] = dispgraph.marker.y
        return d
    @s.when(Baz)
    def udf_baz(dispgraph, value, **kwargs):
        d = dispgraph.super(Baz)(value, **kwargs)
        d['z'] = dispgraph.marker.z
        return d
    result = s(Baz(12,14,16), None)
    assert result == dict(x=12, y=14, z=16), result

def test_parent():
    s = undictify.sub()
    @s.when(SchemaMapping)
    def udf_schema(dispgraph, value, **kwargs):
        d = dispgraph.parent(s)(value, **kwargs)
        d['_extra_data'] = "EXTRA"
        return d
    g = vg.from_flat({
        '': SchemaMapping(),
        'x': Int(),
        'y': List(),
        'y/sub': Int(),
    })
    d = s(g, {'x':12, 'y':[1, 2, 3]})
    assert d == dict(x = 12, y = [1,2,3], _extra_data = 'EXTRA')

def test_superparent():
    class Foo(Marker): pass
    class Bar(Foo): pass
    d1 = make_dispatcher()
    d2 = d1.sub()
    @d1.when(Foo)
    def d1_foo(dispgraph, **kw):
        return "d1_foo"
    @d1.when(Bar)
    def d1_bar(dispgraph, **kw):
        return "d1_bar " + dispgraph.super(Bar)()
    @d2.when(Foo)
    def d2_foo(dispgraph, **kw):
        return "d2_foo " + dispgraph.parent(d2)()
    @d2.when(Bar)
    def d2_bar(dispgraph, **kw):
        return ["d2_bar "+dispgraph.parent(d2)(), "d2_bar "+dispgraph.super(Bar)()]

    parent_super, super_parent = d2(Bar())
    assert parent_super == 'd2_bar d1_bar d1_foo', parent_super
    assert super_parent == 'd2_bar d2_foo d1_foo', super_parent


def test_doublesuper():
    class Foo(Marker): pass
    class Bar(Foo): pass
    class Baz(Bar): pass
    d1 = make_dispatcher()
    @d1.when(Foo)
    def d1_foo(dispgraph, **kw):
        return "d1_foo"
    @d1.when(Bar)
    def d1_bar(dispgraph, **kw):
        return "d1_bar " + dispgraph.super(Bar)()

    assert d1(Baz()) == 'd1_bar d1_foo'
