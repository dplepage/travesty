import travesty as tv

import pytest

PointSchema = tv.SchemaMapping().of(
    x = tv.Int(),
    y = tv.Int(),
    label = tv.String(),
)

LineSchema = tv.SchemaMapping().of(
    start = PointSchema,
    end = PointSchema,
)

def mkpoint(x, y, label):
    return dict(x=x, y=y, label=label)

def mkline(x1, y1, x2, y2, label1='start', label2='end'):
    return dict(
        start = mkpoint(x1, y1, label1),
        end = mkpoint(x2, y2, label2),
    )

addone = tv.mutate.sub()
@addone.when(tv.Int)
def addone_int(dispgraph, value, **kw):
    return value+1

def test_clone():
    l = mkline(1, 2, 3, 4)
    l2 = tv.clone(LineSchema, l)
    assert l2 is not l
    assert l2 == l

def test_clone_blank():
    blank = tv.clone(LineSchema, dict(start={}, end={}))
    assert blank == mkline(None, None, None, None, None, None)

def test_clone_invalid():
    with pytest.raises(tv.Invalid) as e:
        tv.clone(LineSchema, 'not a dict', error_mode=tv.CHECK)
    e.match("^type_error - Expected a dict.*")

    with pytest.raises(tv.Invalid) as e:
        tv.clone(LineSchema, {}, error_mode=tv.CHECK_ALL)
    e.match(
        "end: \[type_error - Expected a dict, got <.* 'NoneType'> instead\], "
        "start: \[type_error - Expected a dict, got <.* 'NoneType'> instead\]"
    )

def test_clone_extras():
    l = mkline(1,2,3,4)
    l['other_key'] = 'hello'
    l2 = tv.clone(LineSchema, l)
    assert l2 != l
    assert 'other_key' not in l2

    LineSchemaSave = tv.SchemaMapping(extra_field_policy='save').of(
        start = PointSchema,
        end = PointSchema,
    )
    l2 = tv.clone(LineSchemaSave, l)
    assert l2 == l
    assert l2 is not l

    LineSchemaFail = tv.SchemaMapping(extra_field_policy='error').of(
        start = PointSchema,
        end = PointSchema,
    )
    # failure mode doesn't count unless we're checking errors
    l2 = tv.clone(LineSchemaFail, l)
    assert l2 != l
    assert 'other_key' not in l2
    with pytest.raises(tv.Invalid) as e:
        tv.clone(LineSchemaFail, l, error_mode=tv.CHECK)
    e.match("unexpected_fields - {'keys': .*'other_key'..?}")

def test_mutate():
    l = mkline(1, 2, 3, 4)
    l2 = addone(LineSchema, l)
    assert l2 is l
    assert l2 == mkline(2, 3, 4, 5)

def test_mutate_blank():
    blank = tv.mutate(LineSchema, dict(start={}, end={}))
    assert blank == mkline(None, None, None, None, None, None)

def test_mutate_invalid():
    with pytest.raises(tv.Invalid) as e:
        tv.mutate(LineSchema, 'not a dict', error_mode=tv.CHECK)
    e.match("^type_error - Expected a dict.*")

    with pytest.raises(tv.Invalid) as e:
        tv.mutate(LineSchema, {}, error_mode=tv.CHECK_ALL)
    e.match(
        "end: \[type_error - Expected a dict, got <.* 'NoneType'> instead\], "
        "start: \[type_error - Expected a dict, got <.* 'NoneType'> instead\]"
    )

def test_mutate_extras():
    l = mkline(1,2,3,4)
    l['other_key'] = 5
    l2 = addone(LineSchema, l)
    assert l2 is l
    assert l.pop('other_key') == 5
    assert l == mkline(2,3,4,5)

def test_validate():
    l = mkline(1, 2, 3, 4)
    tv.validate(LineSchema, l)

def test_validate_blank():
    with pytest.raises(tv.Invalid) as e:
        tv.validate(LineSchema, dict(start={}, end={}))
    e.match(
        "end: \["
            "label: \[missing_attr\], "
            "x: \[missing_attr\], "
            "y: \[missing_attr\]\], "
        "start: \["
            "label: \[missing_attr\], "
            "x: \[missing_attr\], "
            "y: \[missing_attr\]\]")

def test_validate_invalid():
    with pytest.raises(tv.Invalid) as e:
        tv.validate(LineSchema, 'not a dict')
    e.match("^type_error - Expected a dict.*")

    with pytest.raises(tv.Invalid) as e:
        tv.validate(LineSchema, {})
    e.match(
        "end: \[missing_attr\], "
        "start: \[missing_attr\]"
    )

def test_validate_extras():
    l = mkline(1,2,3,4)
    l['other_key'] = 5
    LineSchemaSave = tv.SchemaMapping(extra_field_policy='save').of(
        start = PointSchema,
        end = PointSchema,
    )
    LineSchemaFail = tv.SchemaMapping(extra_field_policy='error').of(
        start = PointSchema,
        end = PointSchema,
    )
    tv.validate(LineSchemaSave, l)
    with pytest.raises(tv.Invalid) as e:
        tv.validate(LineSchema, l)
    e.match("unexpected_fields - {'keys': .*'other_key'..?}")
    with pytest.raises(tv.Invalid) as e:
        tv.validate(LineSchemaFail, l)
    e.match("unexpected_fields - {'keys': .*'other_key'..?}")

