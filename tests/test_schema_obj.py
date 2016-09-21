import travesty as tv

import pytest


class Point(tv.SchemaObj):
    field_types = dict(
        x = tv.Int(),
        y = tv.Int(),
        label = tv.String(),
    )

    def __init__(self, x, y, label):
        self.x = x
        self.y = y
        self.label = label

    @property
    def tuple(self):
        return (self.x, self.y, self.label)

    def __eq__(self, other):
        return self.tuple == other.tuple

class Line(tv.SchemaObj):
    field_types = dict(
        start = Point,
        end = Point,
    )
    def __eq__(self, other):
        return self.start == other.start and self.end == other.end

def mkline(x1, y1, x2, y2, label1='start', label2='end'):
    return Line(
        start = Point(x1, y1, label1),
        end = Point(x2, y2, label2),
    )


addone = tv.mutate.sub()
@addone.when(tv.Int)
def addone_int(dispgraph, value, **kw):
    return value+1

class TestClone(object):
    def test_clone(self):
        l = mkline(1, 2, 3, 4)
        l2 = tv.clone(Line, l)
        assert l2 is not l
        assert l2 == l

    def test_clone_invalid(self):
        # Clone doesn't actually care what type the object is, only that it has the
        # right attributes. So cloning an object of the wrong type is just going to
        # give you a lot of missing_attr errors, not a type error.
        with pytest.raises(tv.Invalid) as e:
            tv.clone(Line, None, error_mode=tv.CHECK)
        e.match("missing_attr")

        with pytest.raises(tv.Invalid) as e:
            tv.clone(Line, Line(), error_mode=tv.CHECK_ALL)
        e.match('(.*missing_attr){6}')

class TestMutate(object):
    def test_mutate(self):
        l = mkline(1, 2, 3, 4)
        l2 = addone(Line, l)
        assert l2 is l
        assert l2 == mkline(2, 3, 4, 5)

    def test_mutate_invalid(self):
        for item in [None, 'some string', Line()]:
            with pytest.raises(tv.Invalid) as e:
                tv.mutate(Line, 'not a dict', error_mode=tv.CHECK_ALL)
            e.match("missing_attr")

class TestValidate(object):
    def test_validate(self):
        l = mkline(1, 2, 3, 4)
        tv.validate(Line, l)

    def test_validate_blank(self):
        with pytest.raises(tv.Invalid) as e:
            l = Line()
            del l.start
            del l.end
            tv.validate(Line, l)
        e.match('end: \[missing_attr\], start: \[missing_attr\]')

    def test_validate_type(self):
        with pytest.raises(tv.Invalid) as e:
            tv.validate(Line, 'not a line')
        e.match("^type_error - Expected Line, got str")

    def test_validate_nested(self):
        with pytest.raises(tv.Invalid) as e:
            tv.validate(Line, mkline(1,2,3,'ha'))
        e.match('end: \[y: \[type_error - Expected Integral; got str\]\]')

class TestMisc(object):
    def test_undictify(self):
        with pytest.raises(tv.Invalid) as e:
            tv.undictify(Point, dict(x=1, y=2, label='hi', extra=12))
        e.match("unexpected_fields - {'keys': .*'extra'..?}")

    def test_pointless_validate(self):
        tv.validate(Point, Point(None, None, None), error_mode=tv.IGNORE)

    def test_ignorant_undictify(self):
        x = tv.undictify(Point, dict(x=1, y=2, label='hi', extra=12), error_mode=tv.IGNORE)
        assert x == Point(1,2,'hi')

    def test_extract_obj(self):
        extract_obj = tv.object_marker.extract_obj
        gentle_clone = tv.clone.sub()
        @gentle_clone.when(tv.ObjectMarker)
        def clone_object_gently(dispgraph, value, **kw):
            newvals = extract_obj(dispgraph, value, kw, default_nones=True)
            return dispgraph.marker.construct(newvals, **kw)
        x = gentle_clone(Point, None)
        assert x == Point(None, None, None)

    def test_subfields(self):
        class UnlabeledPoint(tv.SchemaObj):
            field_types = Point.subfields('x', 'y', z=tv.Int())
        a = tv.undictify(UnlabeledPoint, dict(x=1, y=2, z=3))
        tv.validate(UnlabeledPoint, a)
