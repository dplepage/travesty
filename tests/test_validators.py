# -*- coding: utf-8 -*-
import unittest

import travesty as tv

from travesty.validators import \
    InRange, OneOf, RegexMatch, AsciiString, Email, NonEmptyString

class TestInRange(unittest.TestCase):
    def testInference(self):
        SmallInt = InRange(0, 5)
        self.assertIsInstance(SmallInt, tv.Validated)
        self.assertIsInstance(SmallInt.marker, tv.Int)
        self.assertEquals(len(SmallInt.vdators), 1)
        self.assertIsInstance(SmallInt.vdators[0], tv.validators.IsInRange)
        EarlyString = InRange("a", "c")
        self.assertIsInstance(EarlyString, tv.Validated)
        self.assertIsInstance(EarlyString.marker, tv.String)
        self.assertEquals(len(EarlyString.vdators), 1)
        self.assertIsInstance(EarlyString.vdators[0], tv.validators.IsInRange)

    def testUsage(self):
        SmallInt = InRange(0, 5)
        self.assertIsNone(tv.validate(SmallInt, 0))
        with self.assertRaises(tv.Invalid):
            tv.validate(SmallInt, 7)
        with self.assertRaises(tv.Invalid):
            tv.validate(SmallInt, 3.5)

    def testOverride(self):
        SmallNumber = InRange(0, 5, marker=tv.Number())
        self.assertIsNone(tv.validate(SmallNumber, 0))
        self.assertIsNone(tv.validate(SmallNumber, 3.5))

    def testFailure(self):
        with self.assertRaises(ValueError):
            InRange()


class TestOneOf(unittest.TestCase):
    def testInference(self):
        self.assertIsInstance(OneOf("Frodo", "Bilbo").marker, tv.String)
        self.assertIsInstance(OneOf(12, 14).marker, tv.Int)

    def testUsage(self):
        Baggins = OneOf("Frodo", "Bilbo")
        self.assertIsNone(tv.validate(Baggins, "Frodo"))
        with self.assertRaises(tv.Invalid):
            tv.validate(Baggins, "Brandybuck")
        with self.assertRaises(tv.Invalid):
            tv.validate(Baggins, 2+3j)

    def testOverride(self):
        FourthRoot = OneOf(1, 1j, -1, -1j, marker=tv.Complex())
        self.assertIsNone(tv.validate(FourthRoot, 1))
        self.assertIsNone(tv.validate(FourthRoot, 1j))

    def testFailure(self):
        with self.assertRaises(ValueError):
            OneOf()
        with self.assertRaises(TypeError):
            OneOf(random_arg="whatever")

class TestRegexMatch(unittest.TestCase):
    def testIt(self):
        IP = RegexMatch("\d{1,3}(\.\d{1,3}){3}")
        tv.validate(IP, "127.0.0.1")
        with self.assertRaises(tv.Invalid):
            tv.validate(IP, "This is not an IP address.")
        with self.assertRaises(tv.Invalid):
            tv.validate(IP, 127.0+0.1)

class TestAscii(unittest.TestCase):
    def testIt(self):
        tv.validate(AsciiString(), "hello")
        tv.validate(AsciiString(), u"hello")
        with self.assertRaises(tv.Invalid):
            tv.validate(AsciiString(), u"üñîçø∂é")
        with self.assertRaises(tv.Invalid):
            tv.validate(AsciiString(), 12)

class TestEmail(unittest.TestCase):
    def testIt(self):
        tv.validate(Email(), "a@b.co")
        with self.assertRaises(tv.Invalid):
            tv.validate(Email(), u"üñîçø∂é@example.com")
        with self.assertRaises(tv.Invalid):
            tv.validate(Email(), "foo@bar")
        with self.assertRaises(tv.Invalid):
            tv.validate(Email(), "bar.com")
        with self.assertRaises(tv.Invalid):
            tv.validate(Email(), "bar.com@foo")

class TestNonEmptyString(unittest.TestCase):
    def setUp(self):
        self.vdor = NonEmptyString()

    def test_none(self):
        with self.assertRaises(tv.Invalid):
            tv.validate(self.vdor, None)

    def test_empty_string(self):
        with self.assertRaises(tv.Invalid):
            tv.validate(self.vdor, '')

    def test_blank_string(self):
        with self.assertRaises(tv.Invalid):
            tv.validate(self.vdor, ' ')

    def test_non_empty_string(self):
        tv.validate(self.vdor, 'not-empty')
        tv.validate(self.vdor, 'not empty')
        tv.validate(self.vdor, ' not-empty ')

    def test_direct_validation(self):
        with self.assertRaises(tv.Invalid):
            tv.validators.IsNonEmptyString().validate(['not', 'a', 'string'])
