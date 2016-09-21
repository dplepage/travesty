import pytest

import travesty as tv
import vertigo as vg

from travesty.document import Document, DocSet, UnloadedDocumentException
from travesty.document import DoubleLoadException

from helpers import match_asc, expecting_invalid

class Foo(Document):
    field_types = dict(
        bar = tv.String(),
    )

class FooHolder(Document):
    field_types = dict(
        name = tv.String(),
        foos = tv.List().of(Foo),
    )

class LinkedList(Document):
    field_types = lambda cls: dict(
        value = tv.Int(),
        next = tv.Optional.wrap(cls),
    )
LinkedList._finalize_typegraph()

def flatten(l):
    # Don't call on a looped list
    return [l.value] + flatten(l.next) if l else []

def mkfoos(name, *bars):
    '''Create a FooHolder with the specified bars.

    Duplicate values of bar will map to *the same* Foo object.

    For determinism, all the uids will be set to <bar>_uid
    '''
    foos = {}
    for bar in bars:
        foos[bar] = Foo(uid="{}_uid".format(bar), bar=bar)
    return FooHolder(
        uid=name+"_uid",
        name=name,
        foos=[foos[bar] for bar in bars])

def mklist(values, closed=False):
    nodes = [LinkedList(uid="node{}".format(i), value=v)
             for i, v in enumerate(values)]
    for i in range(len(nodes)-1):
        nodes[i].next = nodes[i+1]
    if closed:
        nodes[-1].next = nodes[0]
    return nodes[0]

def test_creation_and_loading():
    f = Foo()
    assert f.uid
    assert f.bar is None
    with pytest.raises(DoubleLoadException):
        f.load(bar="hi")
    f = Foo._create_unloaded("uid0")
    assert f.uid == 'uid0'
    with pytest.raises(UnloadedDocumentException):
        print(f.bar)
    with pytest.raises(AttributeError):
        print(f.baz)
    f.load(bar="hi")
    assert f.bar == 'hi'
    with pytest.raises(DoubleLoadException):
        f.load(bar="ho")
    assert f.bar == 'hi'


def test_typegraph():
    tg = Foo.typegraph
    assert isinstance(tg.value, Foo.marker_cls)
    assert set(tg.key_iter()) == {'bar', 'uid'}


def test_str_repr():
    f = Foo(uid='fake_uid')
    assert str(f) == '<Foo: fake_uid>', str(f)
    assert repr(f) == str(f)


def test_clone():
    f = mkfoos("test", "hi", "ho", "he", "hi")
    copy = tv.clone(FooHolder, f)
    assert copy is not f
    assert copy.name == 'test'
    assert [x.bar for x in copy.foos] == ['hi', 'ho', 'he', 'hi']
    assert [a is not b for (a,b) in zip(f.foos, copy.foos)]
    assert copy.foos[0] is copy.foos[-1]
    assert f.uid == copy.uid
    assert all(a.uid == b.uid for (a,b) in zip(f.foos, copy.foos))


def test_recursive_clone():
    l = mklist([1, 2, 3], closed=True)
    copy = tv.clone(LinkedList, l)
    assert copy.value == 1
    assert copy.next.value == 2
    assert copy.next.next.value == 3
    assert copy.next.next.next is copy


def test_mutate():
    l = mkfoos("test", "hi", "ho", "he", "hi")

    string_expander = tv.mutate.sub()
    @string_expander.when(tv.String)
    def expand_string(dispgraph, value, **kw):
        print("EXPAND:", value)
        return value+"_"
    string_expander(FooHolder, l)
    assert l.name == 'test_'
    assert [x.bar for x in l.foos] == ['hi_', 'ho_', 'he_', 'hi_']


def test_dictify():
    l = mklist([1, 2, 3], closed=True)
    assert tv.dictify(LinkedList, l) == dict(
        uid = 'node0',
        value = 1,
        next = dict(
            uid = 'node1',
            value = 2,
            next = dict(
                uid = 'node2',
                value = 3,
                next = dict(uid='node0'))))

def test_undictify():
    l = tv.undictify(LinkedList, dict(
        uid = 'node0',
        value = 1,
        next = dict(
            uid = 'node1',
            value = 2,
            next = dict(
                uid = 'node2',
                value = 3,
                next = dict(uid='node0')))))
    assert l.uid == 'node0'
    assert l.value == 1
    assert l.next.uid == 'node1'
    assert l.next.value == 2
    assert l.next.next.uid == 'node2'
    assert l.next.next.value == 3
    assert l.next.next.next is l

def test_misc_failures():
    with expecting_invalid("type_error"):
        tv.validate(Foo, 12)
    with expecting_invalid("type_error"):
        tv.undictify(Foo, 12)
    with expecting_invalid("missing_key:uid"):
        tv.undictify(Foo, {})
    with expecting_invalid("unexpected_fields"):
        tv.undictify(Foo, {'uid':'fake_uid', 'extra_field':12})
    f = Foo._create_unloaded('fake_uid')
    with pytest.raises(TypeError):
        f.load(extra_field = 12)


def test_docset_errors():
    f1 = Foo(bar='hi')
    f2 = Foo(bar='ho')
    d = DocSet([f1])
    d.add(f2)
    with pytest.raises(DoubleLoadException):
        d.load(Foo, {'uid':f1.uid})
    assert d.load(Foo, {'uid':f1.uid}, allow_double_load=True) is f1
    with expecting_invalid('type_error'):
        d.load(Foo, 12)

def test_docset_loading():
    holder = FooHolder(
        uid="theholder",
        name="The Holder of Foo",
        foos = [
            Foo(uid="fooa", bar="a"),
            Foo(uid="foob", bar="b"),
            Foo(uid="fooc", bar="c"),
        ]
    )
    x = tv.dictify(FooHolder, holder)
    d = DocSet()
    holder2 = d.load(FooHolder, x)
    assert holder2.loaded
    assert holder2.uid == holder.uid
    assert len(holder2.foos) == 3
    assert holder2.foos[0].loaded

def test_traverse_docs():
    holder = FooHolder(
        uid="theholder",
        name="The Holder of Foo",
        foos = [
            Foo(uid="fooa", bar="a"),
            Foo(uid="foob", bar="b"),
            Foo(uid="fooc", bar="c"),
        ]
    )
    assert tv.dictify(FooHolder, holder) == {
        'uid': 'theholder',
        'name': 'The Holder of Foo',
        'foos': [
            {'bar': 'a', 'uid': 'fooa'},
            {'bar': 'b', 'uid': 'foob'},
            {'bar': 'c', 'uid': 'fooc'},
        ],
    }
    extras = dict(traverse_docs=vg.from_flat({'':True}))
    assert tv.dictify(FooHolder, holder, extras_graphs=extras) == {
        'uid': 'theholder',
        'name': 'The Holder of Foo',
        'foos': [
            {'uid': 'fooa'},
            {'uid': 'foob'},
            {'uid': 'fooc'},
        ],
    }
    match_asc(tv.graphize(FooHolder, holder, extras_graphs=extras), """
        root: <FooHolder: theholder>
          +--foos: [<Foo: fooa>, <Foo: foob>, <Foo: fooc>]
          |  +--0: <Foo: fooa>
          |  |  +--uid: 'fooa'
          |  +--1: <Foo: foob>
          |  |  +--uid: 'foob'
          |  +--2: <Foo: fooc>
          |     +--uid: 'fooc'
          +--name: 'The Holder of Foo'
          +--uid: 'theholder'
    """)
    match_asc(tv.graphize(FooHolder, holder), """
        root: <FooHolder: theholder>
          +--foos: [<Foo: fooa>, <Foo: foob>, <Foo: fooc>]
          |  +--0: <Foo: fooa>
          |  |  +--bar: 'a'
          |  |  +--uid: 'fooa'
          |  +--1: <Foo: foob>
          |  |  +--bar: 'b'
          |  |  +--uid: 'foob'
          |  +--2: <Foo: fooc>
          |     +--bar: 'c'
          |     +--uid: 'fooc'
          +--name: 'The Holder of Foo'
          +--uid: 'theholder'
    """)
    h1 = tv.clone(FooHolder, holder)
    h2 = tv.clone(FooHolder, holder, extras_graphs=extras)
    assert h1.foos[0] is not holder.foos[0]
    assert h2.foos[0] is holder.foos[0]

    # A linked list with traverse_docs that only goes 3 deep
    l = mklist([1,2,3,4,5])
    extras = dict(traverse_docs=vg.from_flat({
        '': True,
        'next': True,
        'next/next': True
    }))


    sum_ints = tv.traverse.sub()
    @sum_ints.when(tv.Int)
    def add_int(dispgraph, value, **kw):
        kw['accum'][0] = kw['accum'][0]+value

    x = [0]
    sum_ints(LinkedList, l, accum=x)
    assert x[0] == 15
    x = [0]
    sum_ints(LinkedList, l, accum=x, extras_graphs=extras)
    assert x[0] == 6

    double_ints = tv.mutate.sub()
    @double_ints.when(tv.Int)
    def double_int(dispgraph, value, **kw):
        return value*2

    double_ints(LinkedList, l)
    assert flatten(l) == [2,4,6,8,10]
    double_ints(LinkedList, l, extras_graphs = extras)
    assert flatten(l) == [4,8,12,8,10]

def test_ignorant_undictify():
    f = tv.undictify(Foo, dict(uid='hi', bar='ho'), error_mode=tv.IGNORE)
    assert f.uid == 'hi'
    assert f.bar == 'ho'

def test_clone_error_checking():
    with pytest.raises(tv.Invalid) as e:
        tv.clone(FooHolder, None, error_mode=tv.CHECK)
    e.match('type_error - Expected FooHolder, got NoneType')
    # Run it once for branch coverage
    tv.clone(FooHolder, mkfoos("test", "hi"), error_mode=tv.CHECK)

def test_clone_unloaded():
    x = FooHolder._create_unloaded('foo')
    y = tv.clone(FooHolder, x)
    assert y is not x
    assert y.loaded == x.loaded
    assert y.uid == 'foo'

def test_graphize_unloaded():
    x = FooHolder._create_unloaded('foo')
    match_asc(tv.graphize(FooHolder, x), '''
        root: <Unloaded FooHolder: foo>
          +--uid: 'foo'
    ''')

def test_graphize_recursive():
    x = mklist([1,2,3], closed=True)
    match_asc(tv.graphize(LinkedList, x), '''
        root: <LinkedList: node0>
          +--next: <LinkedList: node1>
          |  +--next: <LinkedList: node2>
          |  |  +--next - recursive copy of root
          |  |  +--uid: 'node2'
          |  |  +--value: 3
          |  +--uid: 'node1'
          |  +--value: 2
          +--uid: 'node0'
          +--value: 1
    ''')

