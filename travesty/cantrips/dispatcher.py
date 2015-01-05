from __future__ import unicode_literals
from collections import Counter, namedtuple


def _merge_one(lists, tails):
    for list in lists:
        if not list: continue
        h = list[0]
        if not tails[h]: break
    else:
        raise ValueError("Cannot create a consistent merge order for lists.")
    i = 0
    while i < len(lists):
        list = lists[i]
        if not list:
            lists.remove(list)
            continue
        if list[0] == h:
            list.pop(0)
            if not list:
                lists.remove(list)
                continue
            tails.subtract((list[0],))
        i += 1
    return h

def _merge(lists):
    tails = Counter()
    for list in lists:
        tails.update(list[1:])
    while lists:
        yield _merge_one(lists, tails)

def merge(lists):
    '''Merge several lists, preserving relative order.

    Raises an exception if this is impossible.

    >>> merge([[1,3,5], [2,3,6], [7]])
    [1, 2, 3, 5, 6, 7]
    >>> merge([[], [9,5,1], [10,5,1], [8,5,1], []])
    [9, 10, 8, 5, 1]
    >>> merge([[1, 2], [2, 1]])
    Traceback (most recent call last):
        ...
    ValueError: Cannot create a consistent merge order for lists.
    '''
    return list(_merge([list(l) for l in lists]))

def slice_at(list, value):
    '''Get all items in a list after the first occurrence of value.

    >>> slice_at(['a', 'b', 'c', 'd'], 'b')
    ['c', 'd']

    '''
    return list[list.index(value)+1:]

# SuperMarker is like super() for dispatch targets.
# If dispatcher(val) dispatches with the keys [k1, k2, k3], then
# dispatcher(SuperMarker(k1, val)) will dispatch with the keys [k2, k3].
SuperMarker = namedtuple('SuperMarker', ['key', 'val'])

class _BaseDispatcher(object):
    '''Abstract base class for Dispatcher and DispatchSuper.

    Subclasses must provide .dispatch_mro and ._to_keys(val)
    '''
    def get_default(self):
        for dispatcher in self.dispatch_mro:
            if dispatcher._default:
                return dispatcher._default

    def _dispatch(self, key):
        for dispatcher in self.dispatch_mro:
            v = dispatcher._self_dispatch(key)
            if v is not None:
                return v
        return None

    def dispatch(self, val):
        '''Get a function for a value. Returns None if none is set.'''
        if isinstance(val, SuperMarker):
            start_key, val = val
        else:
            start_key = None
        keys = self._to_keys(val)
        if start_key:
            keys = keys[keys.index(start_key)+1:]
        for key in keys:
            fn = self._dispatch(key)
            if fn:
                return fn
        return self.get_default()

    def call(self, val, *args, **kwargs):
        '''Invoke the dispatch target on val.

        The arguments to the function will be (self, val, *args, **kwargs).
        '''
        fn = self.dispatch(val)
        if fn is None:
            raise NotImplementedError(self._to_keys(val))
        if isinstance(val, SuperMarker):
            val = val[1]
        return fn(self, val, *args, **kwargs)

    def __call__(self, val, *args, **kwargs):
        '''Synonym for self.call()'''
        return self.call(val, *args, **kwargs)

class Dispatcher(_BaseDispatcher):
    '''Dispatcher that chooses a function based on the first argument.

    A dispatcher is a collection of similar functions plus a mechanism for
    deciding which function to call based on a single value. Each dispatcher has
    a dictionary mapping keys to functions, and a keyfn that maps values to
    lists of keys. It selects a function for a value by invoking the keyfn and
    checking each key until it finds one in its dictionary.

    By default, the keyfn uses the MRO of the type of the first argument:

    >>> d = Dispatcher()
    >>> @d.when(int)
    ... def d_int(d, v):
    ...     return "{} is an integer.".format(v)
    >>> @d.when(bool)
    ... def d_bool(d, v):
    ...     return "{} is a boolean.".format(v)
    >>> d.dispatch(12) is d_int
    True
    >>> d.dispatch(True) is d_bool
    True
    >>> d.dispatch(4+3j) is None
    True


    Dispatchers are callable. When called, a dispatcher will dispatch according
    to the first argument of the call and invoke that function, passing in the
    dispatcher itself and all the call arguments:

    >>> d(12)
    '12 is an integer.'
    >>> d(False)
    'False is a boolean.'
    >>> d(3j)
    Traceback (most recent call last):
        ...
    NotImplementedError: (<class 'complex'>, <class 'object'>)


    You can provide a custom keyfn for more complex dispatch. For example,
    consider the following keyfn that returns all prefix paths of a
    '/'-delimited path:

    >>> import re
    >>> def path_prefixes(s):
    ...     return list(reversed([s[:m.start()] for m in re.finditer('$|/', s)]))
    >>> path_prefixes('foo/bar/baz')
    ['foo/bar/baz', 'foo/bar', 'foo']

    Then a dispatcher with this keyfn will check "foo/bar/baz", "foo/bar", and
    "foo" until it finds a match:

    >>> fmt_error = Dispatcher(keyfn=path_prefixes)
    >>> @fmt_error.when("bad_email")
    ... def general_email(d, v):
    ...     return "Invalid Email"
    >>> @fmt_error.when("bad_email/fmt")
    ... def no_at(d, v):
    ...     return "Invalid Email Format"
    >>> @fmt_error.when("bad_email/fmt/no_at")
    ... def no_at(d, v):
    ...     return "Email must contain an @"
    >>> fmt_error("bad_email")
    'Invalid Email'
    >>> fmt_error("bad_email/fmt/no_at")
    'Email must contain an @'
    >>> fmt_error("bad_email/fmt/bad_domain")
    'Invalid Email Format'


    The key function can be anything that returns a list of keys:

    >>> d = Dispatcher(keyfn=lambda x:range(len(x), 0, -1))
    >>> @d.when(3)
    ... def d3(d, v):
    ...     return "{} is length 3.".format(v)
    >>> @d.when(4)
    ... def d4(d, v):
    ...     return "THERE ARE FOUR LIGHTS!"
    >>> @d.default()
    ... def dn(d, v):
    ...     return "I only know three and four."
    >>> d('foo')
    'foo is length 3.'
    >>> d([1,2,3])
    '[1, 2, 3] is length 3.'
    >>> d({'a', 'b', 'c', 'd'})
    'THERE ARE FOUR LIGHTS!'
    >>> d([])
    'I only know three and four.'
    >>> d('this string has more than four characters')
    'THERE ARE FOUR LIGHTS!'

    If you dispatch on a SuperMarker value, then all keys up to the SuperMarker's
    key will be skipped, similar to the behavior of the builtin super() type:

    >>> fmt_error(SuperMarker('bad_email/fmt', 'bad_email/fmt/no_at'))
    'Invalid Email'

    Finally, each dispatcher has an optional list of parents. You can pass this
    in on initialization, or call the .sub() method of an existing dispatcher to
    create a new dispatcher with the same keyfn and with that dispatcher as its
    sole parent.

    If a dispatcher doesn't have an entry for its key, it will check its parents
    before moving on to the next key. This allows a kind of inheritance:


    >>> my_fmt_error = fmt_error.sub()
    >>> @my_fmt_error.when("bad_email/fmt/bad_domain")
    ... def bad_domain(d, v):
    ...     return "The domain is invalid"
    >>> my_fmt_error("bad_email/fmt/no_at") # calls the parent's dispatch result
    'Email must contain an @'
    >>> my_fmt_error("bad_email/fmt/bad_domain")
    'The domain is invalid'

    Multiple inheritance behaves as you would expect:

    >>> alt_fmt_error = fmt_error.sub()
    >>> @alt_fmt_error.when("bad_email/fmt/no_at")
    ... def alt_no_at(d, v):
    ...     return "You need an @"

    >>> joint_fmt_error = Dispatcher(parents=[my_fmt_error, alt_fmt_error])
    >>> joint_fmt_error("bad_email/fmt/no_at") # inherits no_at from alt_
    'You need an @'
    >>> joint_fmt_error("bad_email/fmt/bad_domain") # inherits bad_domain from my_
    'The domain is invalid'


    Note that the dispatched functions always take the dispatcher itself as the
    first argument. This allows for recursive dispatchers. For example, consider
    dispatch based on types:

    >>> handle = Dispatcher(keyfn=lambda x:type(x).__mro__)
    >>> @handle.when(object)
    ... def handle_obj(handle, obj, indent=''):
    ...     print('{}{}'.format(indent, obj))
    >>> @handle.when(list)
    ... def handle_list(handle, l, indent=''):
    ...     print('{}List:'.format(indent))
    ...     for item in l:
    ...         handle(item, indent+'  ')


    This dispatcher prints objects, splitting apart lists:

    >>> x = [1, 2.0, ['abc', 'foo', 107]]
    >>> handle(x)
    List:
      1
      2.0
      List:
        abc
        foo
        107

    We can "subclass" this handler using the .sub() method, and add custom
    handling for a specific type:

    >>> handle2 = handle.sub()
    >>> @handle2.when(int)
    ... def handle_int(handle, i, indent=''):
    ...     print('{}The number {}'.format(indent, i))

    Because the handle_list function takes the dispatcher itself as its first
    argument, this sub-dispatcher can use the same list handler while ensuring
    that it itself will be used on sub-elements:

    >>> handle2(x)
    List:
      The number 1
      2.0
      List:
        abc
        foo
        The number 107
    '''
    def __init__(self, mapping=None, default=None, keyfn=None, parents=()):
        self.mapping = mapping.copy() if mapping else {}
        self._default = default
        self.keyfn = keyfn
        if parents:
            self.dispatch_mro = (self,) + tuple(merge(p.dispatch_mro for p in parents))
            if self.keyfn is None:
                self.keyfn = parents[0].keyfn
        else:
            self.dispatch_mro = (self,)

    def _to_keys(self, val):
        '''Convert a value to a list of keys.'''
        if self.keyfn:
            return self.keyfn(val)
        return type(val).__mro__

    def register(self, keys, fn):
        '''Register fn as the target for each key in keys'''
        for key in keys:
            self.mapping[key] = fn
        return fn

    def when(self, *keys):
        '''Decorator version of .register()'''
        def decorate(fn):
            return self.register(keys, fn)
        return decorate

    def set_default(self, fn):
        '''Set the default function to call for keys that aren't defined.

        If None, then invoking a dispatcher on an unrecognized key will raise a
        NotImplementedError.
        '''
        self._default = fn

    def default(self):
        '''Decorator version of set_default'''
        def decorate(fn):
            self.set_default(fn)
            return fn
        return decorate

    def _self_dispatch(self, key):
        if key in self.mapping:
            return self.mapping[key]
        return None

    def sub(self):
        '''Create a new dispatcher with the same keyfn and self as a parent.'''
        return Dispatcher(parents=[self], keyfn=self.keyfn)

class DispatchSuper(_BaseDispatcher):
    '''
    Like super(), but for dispatchers.

    >>> import re
    >>> def path_prefixes(s):
    ...     return list(reversed([s[:m.start()] for m in re.finditer('$|/', s)]))

    >>> disp = Dispatcher(keyfn=path_prefixes)
    >>> @disp.when("recurse")
    ... def disp_recurse(d, s, val):
    ...     print(val)
    ...     if val > 0:
    ...         d(s, val-1)
    >>> disp2 = Dispatcher(parents=[disp])
    >>> @disp2.when("recurse")
    ... def disp2_recurse(d, s, val):
    ...     print("From disp2!")
    ...     DispatchSuper(disp2, d)(s, val)
    >>> disp2("recurse", 5)
    From disp2!
    5
    From disp2!
    4
    From disp2!
    3
    From disp2!
    2
    From disp2!
    1
    From disp2!
    0

    Super supports defaults as well - if the parent has none, it will fail as
    you'd expect:

    >>> @disp2.when("not_implemented_in_parent")
    ... def disp2_niip(d, s, val):
    ...     print("This will hit parent's default, which is not implemented.")
    ...     DispatchSuper(disp2, d)(s, val)
    >>> disp2("not_implemented_in_parent", 5)
    Traceback (most recent call last):
        ...
    NotImplementedError: ['not_implemented_in_parent']

    If a parent dispatcher does have a default, it gets called:

    >>> @disp.default()
    ... def disp_default(d, s, val):
    ...     print("It is implemented now!")

    >>> disp2("not_implemented_in_parent", 5)
    This will hit parent's default, which is not implemented.
    It is implemented now!

    '''
    def __init__(self, above_disp, disp):
        self.disp = disp
        self.above_disp = above_disp
        self.dispatch_mro = slice_at(self.disp.dispatch_mro, self.above_disp)

    def _to_keys(self, val):
        return self.disp._to_keys(val)

    def call(self, val, *args, **kwargs):
        # Need to override base so that we pass in self.disp instead of self
        fn = self.dispatch(val)
        if fn is None:
            raise NotImplementedError(self._to_keys(val))
        return fn(self.disp, val, *args, **kwargs)
