from travesty import Invalid, Int, String, SchemaObj, Optional
from travesty import dictify, undictify, validate, traverse

class BCSchemaObj(SchemaObj):
    def dictify(self, **kwargs):
        return dictify(type(self), self, **kwargs)
    @classmethod
    def undictify(cls, value, **kwargs):
        return undictify(cls, value, **kwargs)
    def traverse(self, **kwargs):
        return traverse(type(self), self, **kwargs)
    def validate(self, **kwargs):
        return validate(type(self), self, **kwargs)

class Point(BCSchemaObj):
    field_types = {
        'x': Int(),
        'y': Int(),
        'label': String(),
    }
    def __init__(self, x, y, label='foo'):
        super(Point, self).__init__()
        self.x = x
        self.y = y
        self.label = label

plain_data = {'x':-12, 'y':1, 'label':'foo'}
blank_data = {}
bad_data = {'x':'hi', 'y':-1, 'label':'blarg'}
extra_data = {'x':-12, 'y':1, 'label':'foo', 'ex':['foo','bar'], 'ex2':'hi'}

def test_basic():
    p = Point.undictify(plain_data)
    assert p.x == -12
    assert p.y == 1
    assert p.label == 'foo'
    assert p.dictify() == plain_data, p.dictify()

def test_errors():
    try:
        p = Point.undictify(bad_data)
        p.validate()
    except Invalid as e:
        assert e.sub_errors['x'][0].err_id == 'type_error'
    else:
        assert False

def test_extra():
    try:
        Point.undictify(extra_data)
    except Invalid as e:
        assert len(e.own_errors) == 1
        err = e.own_errors[0]
        assert err.err_id == 'unexpected_fields', err
        assert err.kwargs['keys'] == {'ex', 'ex2'}
    else:
        assert False

def test_inheritance():
    class UnlabeledPoint(Point):
        field_types = {'label':None, 'color':String()}
    try:
        undictify(UnlabeledPoint, plain_data)
    except Invalid as e:
        assert not e.sub_errors
        assert len(e.own_errors) == 1
        assert e.own_errors[0].err_id == 'unexpected_fields'
        assert e.own_errors[0].kwargs == {'keys':{'label'}}
    else:
        assert False
    color_data = dict(x=12, y=1, color='blue')
    p = undictify(UnlabeledPoint, color_data)
    assert p.color == 'blue'

def test_construct():
    p = Point(-12,1)
    assert p.dictify() == plain_data

def test_subfields():
    assert Point.subfields("x", "y") == dict(
        x = Point.field_types['x'],
        y = Point.field_types['y'])
    tmp = Optional.wrap(String())
    sf = Point.subfields("label", x=tmp, z=tmp)
    assert sf == dict(
        label = Point.field_types['label'],
        x = tmp,
        z = tmp,
    )

class TwoPoints(BCSchemaObj):
    field_types = dict(a=Point, b=Point)

def test_nested():
    x = TwoPoints.undictify(dict(a=plain_data, b=plain_data))
    assert x.a.x == x.b.x == -12
    assert x.dictify() == dict(a=plain_data, b=plain_data)


def test_recursive():
    # TODO There should be a more elegant way to generate recursive schemas
    class LinkedNode(SchemaObj):
        field_types = lambda cls: dict(
            val = Int(),
            next = Optional.wrap(cls),
        )
    LinkedNode._finalize_typegraph()
    l = LinkedNode(val=12, next=LinkedNode(val=12, next=None))
    validate(LinkedNode, l)
    l.next.next = "hi"
    try:
        validate(LinkedNode, l)
    except Invalid as e:
        err = e.sub_errors['next'].sub_errors['next'].own_errors[0]
        assert err.err_id == 'type_error'
    else:
        raise Exception("That should have failed.")

test_recursive()
