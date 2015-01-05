from . import Wrapper, validate, InvalidAggregator

class Validated(Wrapper):
    '''Wrapper that specifies additional validators for a marker.

    >>> from travesty import Int
    >>> from travesty.validators import IsOneOf
    >>> typegraph = Validated.wrap(Int(), [IsOneOf([1,2,3])])
    >>> validate(typegraph, 2)
    >>> validate(typegraph, 15)
    Traceback (most recent call last):
        ...
    Invalid: invalid_choice

    Note that the type's validator is run first, and extra validators aren't run
    unless it passes. So e.g. if we pass a non-int in with our typegraph, we get
    a type_error instead of an invalid_choice.

    >>> validate(typegraph, "hello")
    Traceback (most recent call last):
        ...
    Invalid: type_error
    '''
    def __init__(self, marker, vdators=()):
        super(Validated, self).__init__(marker)
        self.vdators = tuple(vdators)

    @classmethod
    def wrap(cls, marker, vdators=()):
        return super(Validated, cls).wrap(marker, vdators=vdators)

@validate.when(Validated)
def validate_validated(dispgraph, value, **kwargs):
    validated = dispgraph.marker
    # If core validation fails, don't bother with higher-level validation
    dispgraph.for_marker(validated.marker)(value, **kwargs)
    # Now run each extra validator in turn
    fail_early = kwargs.get("dfy_fail_early", False)
    error_agg = InvalidAggregator(autoraise = fail_early)
    for vdator in validated.vdators:
        with error_agg.checking():
            dispgraph.for_marker(vdator)(value, **kwargs)
    error_agg.raise_if_any()
