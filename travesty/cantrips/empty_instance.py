class _EmptyOldClass:
    '''Placeholder old style class assembling blank instances.'''
    pass


class _EmptyNewClass(object):
    '''Placeholder new style class assembling blank instances.'''
    pass


def empty_instance(cls):
    '''Create an instance of cls without invoking cls.__init__.

    Supports both old- and new-style classes:

    >>> class Foo:
    ...     def __init__(self, x):
    ...         self.x = x
    >>> class Bar(object):
    ...     def __init__(self, x):
    ...         self.x = x
    >>> foo = empty_instance(Foo)
    >>> bar = empty_instance(Bar)
    >>> hasattr(foo, 'x')
    False
    >>> hasattr(bar, 'x')
    False

    '''
    if issubclass(cls, object):
        instance = _EmptyNewClass()
    else: # pragma: no cover
        instance = _EmptyOldClass()
    instance.__class__ = cls
    return instance

def create_instance(cls, kwargs):
    '''Create and populate an instance of cls.

    >>> class Bar(object): pass
    >>> b = create_instance(Bar, dict(x=12))
    >>> b.x
    12
    '''
    instance = empty_instance(cls)
    for key, val in kwargs.items():
        setattr(instance, key, val)
    return instance

def ctor(cls):
    '''Return a constructor function for cls.

    >>> class Bar(object): pass
    >>> make_bar = ctor(Bar)
    >>> b = make_bar(x=12, y=14)
    >>> b.x
    12
    >>> b.y
    14

    '''
    return lambda **kwargs: create_instance(cls, kwargs)