from contextlib import contextmanager
import textwrap

import vertigo as vg

from travesty import Invalid

class Report(object):
    error = None

@contextmanager
def expecting(error_type):
    ename = error_type.__name__
    r = Report()
    try:
        yield r
    except error_type as e:
        r.error = e
        return
    except Exception as e:
        ename2 = type(e).__name__
        msg = "Expected {}, got {}:'{}' instead".format(ename, ename2, e)
        raise Exception(msg)
    else:
        raise Exception("Expected {}".format(ename))

@contextmanager
def expecting_invalid(msg):
    with expecting(Invalid) as e:
        yield e
    assert e.error.id_string() == msg, e.error.id_string()


def match_asc(g, s):
    x = vg.ascii_tree(g, sort=True)
    assert x == textwrap.dedent(s).strip(), x

