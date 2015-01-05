# -*- coding: utf-8 -*-
import re
import sys

if sys.version >= '3': # pragma: no cover
    unicode = str
    basestring = str

from .base import Marker, validate
from .typed_leaf import String
from .invalid import Invalid
from .validated import Validated
from .inference import infer_marker

class Validator(Marker):
    '''Validators are plug-ins to add advanced validation.

    They define a .validate(value, **kwargs) function, which raises an Invalid
    if the value is invalid and otherwise does nothing.

    You can pass a list of validators to the Validated wrapper type to apply
    advanced validation.

    Validator is actually a Marker subclass, so you can use it directly in a
    typegraph, but in general there should be no reason to do so - prefer to
    use it in conjunction with Validated.
    '''
    def validate(self, value, **kwargs): # pragma: no cover
        raise NotImplementedError()

    def of(self, marker):
        return Validated(marker, [self])

@validate.when(Validator)
def validate_validator(dispgraph, value, **kwargs):
    dispgraph.marker.validate(value, **kwargs)

class IsInRange(Validator):
    '''Require values to be between two endpoints.

    The endpoints themselves are allowed.

    >>> RangeInt = IsInRange(0, 5)
    >>> RangeInt.validate(0)
    >>> RangeInt.validate(3)
    >>> RangeInt.validate(5)
    >>> RangeInt.validate(None)
    >>> RangeInt.validate(-1)
    Traceback (most recent call last):
        ...
    Invalid: range_error/too_low
    >>> RangeInt.validate(6)
    Traceback (most recent call last):
        ...
    Invalid: range_error/too_high

    Note that the types can be any type for which < and > are defined:

    >>> from datetime import date
    >>> DateIn2012 = IsInRange(date(2012, 1, 1), date(2012, 12, 31))
    >>> DateIn2012.validate(date(2012, 4, 13))
    >>> DateIn2012.validate(date(2013, 1, 1))
    Traceback (most recent call last):
        ...
    Invalid: range_error/too_high
    '''
    def __init__(self, low=None, high=None):
        self.low = low
        self.high = high

    def validate(self, value, **kwargs):
        if value is None: return
        if self.low is not None and value < self.low:
            raise Invalid("range_error/too_low")
        if self.high is not None and value > self.high:
            raise Invalid("range_error/too_high")

def InRange(low=None, high=None, marker=None):
    '''Require values to be between two endpoints.

    See IsInRange.

    >>> SmallInt = InRange(0, 5)
    >>> SmallInt
    <Validated(Int)>
    >>> EarlyStr = InRange('a', 'h')
    >>> EarlyStr
    <Validated(String)>
    >>> validate(EarlyStr, "azkaban")
    >>> validate(EarlyStr, "zazzerpan")
    Traceback (most recent call last):
        ...
    Invalid: range_error/too_high

    You can override the inferred marker:

    >>> from . import Bytes
    >>> EarlyBytes = InRange(b'A', b'C', marker=Bytes())
    >>> validate(EarlyBytes, b'Angela McAscii')
    >>> validate(EarlyBytes, u'Alric von Üñîçø∂é')
    Traceback (most recent call last):
        ...
    Invalid: type_error
    '''

    if (marker or low or high) is None:
        raise ValueError("low, high, and marker cannot all be None")
    if not marker:
        val = low if low is not None else high
        marker = infer_marker(val)
    return IsInRange(low, high).of(marker)

class IsOneOf(Validator):
    '''Require values to come from a fixed list of options.

    >>> Baggins = IsOneOf(['Frodo', 'Bilbo'])
    >>> Baggins.validate("Bilbo")
    >>> Baggins.validate("Frodo")
    >>> Baggins.validate("Meriadoc")
    Traceback (most recent call last):
        ...
    Invalid: invalid_choice
    '''
    def __init__(self, options):
        self.options = options

    def validate(self, value, **kwargs):
        if value not in self.options:
            raise Invalid("invalid_choice")

# This would take (*options, marker=None) but python2 doesn't allow that
def OneOf(*options, **kwargs):
    '''Require values to come from a fixed list of options.

    This creates a Validated instance with an inferred marker and an IsOneOf
    validator:

    >>> Baggins = OneOf('Frodo', 'Bilbo')
    >>> Baggins
    <Validated(String)>
    >>> Baggins.vdators
    (<IsOneOf>,)
    >>> OneToThree = OneOf(1,2,3)
    >>> OneToThree
    <Validated(Int)>

    Note that the inference is based on the first argument, which may not do
    what you expected with e.g. numeric types:

    >>> from . import Complex
    >>> FourthRootOfUnity = OneOf(1, 1j, -1, -1j)
    >>> FourthRootOfUnity # You might expect a Complex
    <Validated(Int)>

    You can override the inferred marker to get around this:

    >>> FourthRootOfUnity = OneOf(1, 1j, -1, -1j, marker=Complex())
    >>> FourthRootOfUnity
    <Validated(Complex)>

    Note that you must provide a marker if you're creating an empty option
    list for some reason:

    >>> OneOf()
    Traceback (most recent call last):
        ...
    ValueError: Must provide marker or at least one option
    '''

    marker = kwargs.pop("marker", None)
    if kwargs:
        msg = "OneOf() got an unexpected keyword argument '{}'"
        key = next(iter(kwargs.keys()))
        raise TypeError(msg.format(key))
    if marker is None:
        if not options:
            raise ValueError("Must provide marker or at least one option")
        marker = infer_marker(options[0])
    return IsOneOf(options).of(marker)

class MatchesRegex(Validator):
    '''Require non-empty values to match a regular expression.

    >>> IP = MatchesRegex("\d{1,3}(\.\d{1,3}){3}")
    >>> IP.validate("127.0.0.1")
    >>> IP.validate("This is not an IP address.")
    Traceback (most recent call last):
        ...
    Invalid: invalid_string
    >>> IP.validate("127.0.0.no")
    Traceback (most recent call last):
        ...
    Invalid: invalid_string
    >>> IP.validate(12)
    Traceback (most recent call last):
        ...
    Invalid: type_error
    '''
    def __init__(self, regex):
        self.regex = re.compile(regex)

    def validate(self, value, **kwargs):
        if not isinstance(value, basestring):
            raise Invalid("type_error")
        if not self.regex.match(value):
            raise Invalid("invalid_string")

def RegexMatch(regex, marker=String()):
    return MatchesRegex(regex).of(marker)

class IsAsciiString(Validator):
    def validate(self, value, **kwargs):
        if not isinstance(value, basestring):
            raise Invalid("type_error")
        try:
            value.encode('ascii')
        except Exception:
            raise Invalid("not_ascii")

def AsciiString(marker=String()):
    return IsAsciiString().of(marker)

class IsEmail(IsAsciiString):
    '''Require a valid email address.

    Doesn't support weirder email addresses, like those with parentheses.

    >>> email = IsEmail()
    >>> email.validate('dplepage@gmail.com')
    >>> email.validate('madeupname@nowhere.none')
    >>> email.validate('foo AT bar DOT com')
    Traceback (most recent call last):
        ...
    Invalid: invalid_email/no_at
    >>> email.validate('()@bar.com')
    Traceback (most recent call last):
        ...
    Invalid: invalid_email/bad_user
    >>> email.validate('foo@')
    Traceback (most recent call last):
        ...
    Invalid: invalid_email/bad_domain
    >>> email.validate(u'føö@bår.côm')
    Traceback (most recent call last):
        ...
    Invalid: not_ascii
    >>> email.validate(12)
    Traceback (most recent call last):
        ...
    Invalid: type_error

    '''
    # regexes borrowed from formencode.validators
    usernameRE = re.compile(r"^[^ \t\n\r@<>()]+$", re.I)
    domainRE = re.compile(r'''
        ^(?:[a-z0-9][a-z0-9\-]{0,62}\.)+ # (sub)domain - alpha followed by 62max chars (63 total)
        [a-z]{2,}$                       # TLD
    ''', re.I | re.VERBOSE)

    def validate(self, value, **kwargs):
        super(IsEmail, self).validate(value, **kwargs)
        if '@' not in value:
            raise Invalid("invalid_email/no_at")
        user, domain = value.split('@', 1)
        if not self.usernameRE.match(user):
            raise Invalid("invalid_email/bad_user")
        if not self.domainRE.match(domain):
            raise Invalid("invalid_email/bad_domain")

def Email(marker=String()):
    return IsEmail().of(marker)

class IsNonEmptyString(Validator):
    '''Require something more than an empty string.

    >>> not_empty = IsNonEmptyString()
    >>> not_empty.validate(' ')
    Traceback (most recent call last):
        ...
    Invalid: empty
    '''
    def validate(self, value, **kwargs):
        if not isinstance(value, basestring):
            raise Invalid("type_error")
        if len(value.strip()) == 0:
            raise Invalid("empty")

def NonEmptyString(marker=String()):
    return IsNonEmptyString().of(marker)

if __name__ == '__main__': # pragma: no cover
    import doctest
    doctest.testmod()
