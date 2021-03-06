import collections

class ImmutableDict(collections.Mapping):
    '''An immutable dictionary.

    For the most part, it behaves like a normal dictionary, except that you
    can't set items:

    >>> repr(ImmutableDict(a=5))
    "ImmutableDict({'a': 5})"
    >>> d = ImmutableDict(dict(a=1, b=2), x=12, y=14)
    >>> assert d == {'a':1, 'b':2, 'x':12, 'y':14}
    >>> assert len(d) == 4
    >>> assert 'a' in d
    >>> assert 'c' not in d
    >>> d['foo'] = 12
    Traceback (most recent call last):
        ...
    TypeError: 'ImmutableDict' object does not support item assignment

    It also has the .overlay method, which behaves like .update() on a normal
    dict, but returns a new ImmutableDict:

    >>> d2 = d.overlay(dict(a=2, foo='bar'))
    >>> d2 == dict(a=2, b=2, x=12, y=14, foo='bar')
    True

    Overlay also provides a strip_none argument, which defaults to False; if it
    is explicitly set to True, then keys in the new dict that are set to None
    will be dropped (instead of replaced by None):

    >>> not_stripped = d.overlay(dict(a=None, b=None))
    >>> not_stripped == dict(a=None, b=None, x=12, y=14)
    True
    >>> stripped = d.overlay(dict(a=None, b=None), strip_none=True)
    >>> stripped == dict(x=12, y=14)
    True

    The .select method creates a subset of this dict:

    >>> subd = d.select(['a', 'x'])
    >>> subd == dict(a=1, x=12)
    True

    The .omit method is like .select, but blacklisting instead of whitelisting:

    >>> subd = d.omit(['y', 'b'])
    >>> subd == dict(a=1, x=12)
    True

    '''
    def __init__(self, *args, **kwargs):
        self.__dict = dict(*args, **kwargs)

    def __getitem__(self, key):
        return self.__dict[key]

    def __contains__(self, key):
        return key in self.__dict

    def __iter__(self):
        return iter(self.__dict)

    def __len__(self):
        return len(self.__dict)

    def __repr__(self):
        return "ImmutableDict({!r})".format(self.__dict)

    def overlay(self, other, strip_none=False):
        '''
        Create a copy of one dict with values from a new one.

        >>> d = ImmutableDict(a=1, b=2)
        >>> d2 = d.overlay(dict(a=2, foo='bar'))
        >>> assert d2 == {'a':2, 'b':2, 'foo':'bar'}

        If the strip_none argument is True, keys in the new dict that are None
        will be dropped instead of replaced by None:

        >>> not_stripped = d.overlay(dict(a=None))
        >>> not_stripped == dict(a=None, b=2)
        True
        >>> stripped = d.overlay(dict(a=None), strip_none=True)
        >>> stripped == dict(b=2)
        True
        '''
        d = dict(self)
        d.update(other)
        if strip_none:
            for key, value in other.items():
                if value is None:
                    del d[key]
        return ImmutableDict(d)

    def select(self, keys):
        '''
        Create a subdict of an existing dict.

        >>> d = ImmutableDict(a=1, b=2, c=3, d="four")
        >>> d2 = d.select({'a', 'd'})
        >>> assert d2 == dict(a=1, d="four")
        '''
        return ImmutableDict({k:self[k] for k in keys})

    def omit(self, keys):
        '''
        Create a subdict of an existing dict by omitting keys

        >>> d = ImmutableDict(a=1, b=2, c=3, d="four")
        >>> d2 = d.omit({'a', 'd'})
        >>> assert d2 == dict(b=2, c=3)
        '''
        return ImmutableDict({k:self[k] for k in set(self)-set(keys)})

    def select_overlay(self, *keys, **other):
        '''
        Shortand for self.select(keys).overlay(other).

        >>> d = ImmutableDict(a=1, b=2, c=3, d="four")
        >>> d2 = d.select(['a', 'd']).overlay({'b':5})
        >>> d3 = d.select_overlay('a', 'd', b=5)
        >>> assert d2 == d3
        '''
        return self.select(keys).overlay(other)
