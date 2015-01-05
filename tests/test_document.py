from travesty import dictify, undictify, traverse, validate, String, List

from travesty.document import Document, DocSet, UnloadedDocumentException
from travesty.document import DoubleLoadException

from helpers import expecting, match_asc, expecting_invalid

class Foo(Document):
    field_types = dict(bar=String())

class FooHolder(Document):
    field_types = dict(
        name = String(),
        foos = List().of(Foo),
    )

def test_basic():
    f = Foo()
    assert f.uid
    assert f.bar is None
    with expecting(DoubleLoadException):
        f.load(bar="hi")

    f.uid = "uid0" # for string comparison tests

    match_asc(traverse(Foo, f), """
        root: <Foo: uid0>
          +--bar: None
          +--uid: 'uid0'
    """)
    with expecting_invalid("bar: [type_error]"):
        validate(Foo, f)
    f.bar = "hello"
    validate(Foo, f)
    assert dictify(Foo, f) == {'bar':"hello", 'uid':'uid0'}

def test_unloaded():
    f = Foo._create_unloaded('fake_uid')
    assert f.uid == 'fake_uid'

    with expecting(UnloadedDocumentException):
        print(f.bar)
    with expecting(AttributeError):
        print(f.baz)

    match_asc(traverse(Foo, f), """
        root: <Unloaded Foo: fake_uid>
          +--uid: 'fake_uid'
    """)

    assert dictify(Foo, f) == {'uid':f.uid}
    validate(Foo, f)

    del f.uid
    with expecting_invalid("missing_attr"):
        validate(Foo, f)

def test_load_unloaded():
    f = Foo._create_unloaded('fake_uid')
    f.load(bar="hi")
    assert f.bar == "hi"
    assert f.uid == "fake_uid"
    with expecting(AttributeError):
        print(f.baz)
    with expecting(DoubleLoadException):
        f.load(bar="hi")

def test_typegraph():
    tg = Foo.typegraph
    assert isinstance(tg.value, Foo.marker_cls)
    assert set(tg.key_iter()) == {'bar', 'uid'}

def test_str_repr():
    f = Foo(uid='fake_uid')
    assert str(f) == '<Foo: fake_uid>', str(f)
    assert repr(f) == str(f)

def test_misc_failures():
    with expecting_invalid("type_error"):
        validate(Foo, 12)
    with expecting_invalid("type_error"):
        undictify(Foo, 12)
    with expecting_invalid("missing_key:uid"):
        undictify(Foo, {})
    with expecting_invalid("unexpected_fields"):
        undictify(Foo, {'uid':'fake_uid', 'extra_field':12})
    f = Foo._create_unloaded('fake_uid')
    with expecting(TypeError):
        f.load(extra_field = 12)

def test_no_doc_kids():
    holder = FooHolder(
        uid="theholder",
        name="The Holder of Foo",
        foos = [
            Foo(uid="fooa", bar="a"),
            Foo(uid="foob", bar="b"),
            Foo(uid="fooc", bar="c"),
        ]
    )
    a = dictify(FooHolder, holder)
    assert a == {
        'uid': 'theholder',
        'name': 'The Holder of Foo',
        'foos': [
            {'bar': 'a', 'uid': 'fooa'},
            {'bar': 'b', 'uid': 'foob'},
            {'bar': 'c', 'uid': 'fooc'},
        ],
    }, a
    storage = {}
    b = dictify(FooHolder, holder, doc_storage=storage)
    assert b == {
        'uid': 'theholder',
    }, b
    assert storage == {
        'fooa': {'bar': 'a', 'uid': 'fooa'},
        'foob': {'bar': 'b', 'uid': 'foob'},
        'fooc': {'bar': 'c', 'uid': 'fooc'},
        'theholder': {
            'uid': 'theholder',
            'name': 'The Holder of Foo',
            'foos': [{'uid': 'fooa'}, {'uid': 'foob'}, {'uid': 'fooc'}],
        },
    }, storage
    c = dictify(FooHolder, holder, no_doc_kids=True)
    assert c == {
        'uid': 'theholder',
        'name': 'The Holder of Foo',
        'foos': [
            {'uid': 'fooa'},
            {'uid': 'foob'},
            {'uid': 'fooc'},
        ],
    }, c
    storage = {}
    d = dictify(FooHolder, holder, doc_storage=storage, no_doc_kids=True)
    assert d == {
        'uid': 'theholder',
    }, d
    assert storage == {
        'theholder': {
            'uid': 'theholder',
            'name': 'The Holder of Foo',
            'foos': [{'uid': 'fooa'}, {'uid': 'foob'}, {'uid': 'fooc'}],
        },
    }, storage
    match_asc(traverse(FooHolder, holder, no_doc_kids=True), """
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
    match_asc(traverse(FooHolder, holder, no_doc_kids=False), """
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

def test_docset_errors():
    f1 = Foo(bar='hi')
    f2 = Foo(bar='ho')
    d = DocSet([f1])
    d.add(f2)
    with expecting(DoubleLoadException):
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
    storage = {}
    dictify(FooHolder, holder, doc_storage=storage)
    d = DocSet()
    holder2 = d.load(FooHolder, storage['theholder'])
    assert holder2.loaded
    assert holder2.uid == holder.uid
    assert len(holder2.foos) == 3
    assert holder2.foos[0].loaded == False
    with expecting(UnloadedDocumentException):
        holder2.foos[0].bar


def test_undictify():
    f1 = Foo(bar="hi")
    s = dictify(Foo, f1)
    f2 = undictify(Foo, s)
    assert f2.uid == f1.uid
    assert f2.loaded
    assert f2.bar == f1.bar