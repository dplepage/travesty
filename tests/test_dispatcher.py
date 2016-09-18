import pytest

from travesty.cantrips.dispatcher import Dispatcher

def test_default_inheritance():
    add = Dispatcher()
    @add.when(int)
    def add_int(d, v, x):
        return v + x
    assert add(2, x=1) == 3
    with pytest.raises(TypeError):
        add(2)
    add.default_value('x', 1)
    assert add(2) == 3

    mul = add.sub()
    @mul.when(int)
    def mul_int(d, v, x):
        return v * x
    assert mul(2, x=4) == 8
    assert mul(2) == 2
    mul.default_factory('x', lambda:2)
    assert mul(2) == 4
