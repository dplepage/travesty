'''subclass.py: mixin for programmatically subclassable classes.'''
from abc import ABCMeta

class SubclassMixin(object):
    '''SubclassMixin adds a subclass(**kwargs) method to a class.

    cls.subclass(**kwargs) is equivalent to creating a new subclass with the
    contents of kwargs written out within it.

    For example:

    >>> class Point(SubclassMixin):
    ...   round = False
    ...   def __init__(self, x, y):
    ...     if self.round:
    ...        x, y = int(x), int(y)
    ...     self.x, self.y = x, y
    ...
    >>> p = Point(.5, 3.25)
    >>> p.x, p.y
    (0.5, 3.25)

    The following two subclasses are (nearly) equivalent

    >>> class IntPoint1(Point):
    ...   round = True
    ...
    >>> IntPoint2 = Point.subclass(round=True)

    They behave exactly the same:

    >>> p1 = IntPoint1(.5, 3.25)
    >>> p2 = IntPoint2(.5, 3.25)
    >>> p1.x, p1.y
    (0, 3)
    >>> p2.x, p2.y
    (0, 3)

    The only difference is their names, as IntPoint2's name was auto-generated:

    >>> IntPoint1.__name__
    'IntPoint1'
    >>> IntPoint2.__name__
    'Point_sub'

    This can be rectified via the special __class_name attribute:

    >>> IntPoint3 = Point.subclass(round=True, __class_name="IntPoint1")
    >>> IntPoint3.__name__
    'IntPoint1'

    '''
    @classmethod
    def subclass(cls, **kwargs):
        '''
        Programmatically generate subclasses of this class.

        The generated subclass will be called <name of this class>_sub unless
        the special parameter __class_name is passed in.
        '''
        if '__class_name' in kwargs:
            class_name = kwargs.pop('__class_name')
        else:
            class_name = cls.__name__ + "_sub"
        subcls = type(cls)(class_name, (cls,), kwargs)
        return subcls

    @classmethod
    def __subclass__(cls, **kwargs):
        for name, val in kwargs.items():
            setattr(cls, name, val)


def _im_func(fn): # pragma: no cover
    if hasattr(fn, 'im_func'):
        return fn.im_func
    if hasattr(fn, '__func__'):
        return fn.__func__
    return fn

class SubclassableMeta(ABCMeta):
    '''Metaclass for classes that do extra work on subclassing.

    Classes with this metaclass can define a __subclass__(cls, **kwargs) method
    that will be called on subclasses upon creation.

    For example, consider this class, whose __subclass__ renames the 'foo'
    attribute to 'bar':

    >>> class AutoBar(Subclassable):
    ...     def __subclass__(cls, foo=None, **kwargs):
    ...         kwargs.setdefault('bar', foo)
    ...         super(AutoBar, cls).__subclass__(**kwargs)

    Then we can create a subclass of AutoBar:

    >>> class Foo(AutoBar):
    ...     foo = 12

    And it will have a 'bar' attr instead of 'foo':

    >>> Foo.bar
    12
    >>> Foo.foo
    Traceback (most recent call last):
        ...
    AttributeError: type object 'Foo' has no attribute 'foo'


    Note that __subclass__ is NOT be called on the root class, so AutoBar itself
    has no 'bar' attr:

    >>> AutoBar.bar
    Traceback (most recent call last):
        ...
    AttributeError: type object 'AutoBar' has no attribute 'bar'
    '''
    def __new__(cls, name, supers, kwargs):
        t = ABCMeta.__new__(cls, name, supers, {})
        # Force __subclass__ to be a classmethod
        # if not isinstance(t.__subclass__, classmethod):
        #     t.__subclass__ = classmethod(_im_func(t.__subclass__))
        if '__subclass__' in kwargs:
            sc = kwargs['__subclass__']
            if not isinstance(sc, classmethod):
                kwargs['__subclass__'] = classmethod(sc)
        t.__subclass__(**kwargs)
        return t

Subclassable = SubclassableMeta('Subclassable', (SubclassMixin,), {})
