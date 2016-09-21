import travesty as tv

import pytest

def test_agg_loop():
    # Test for previous bug where an aggregator would get caught in a loop if it
    # raised its own exception while it was watching for exceptions
    with pytest.raises(tv.Invalid) as e:
        with tv.base.aggregating_errors(tv.CHECK) as agg:
            with agg.checking_sub("foo"):
                agg.own_error(tv.Invalid("ok"))
    e.match('ok')

    with pytest.raises(tv.Invalid) as e:
        with tv.base.aggregating_errors(tv.CHECK) as agg:
            with agg.checking():
                raise tv.Invalid("ok")
    e.match('ok')
