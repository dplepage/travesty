import functools

def has_cache(fn):
    '''Add a cache dictionary to a function.

    The function must accept a keyword-only argument named 'cached'. If cache is
    provided when calling this function, it will be used normally; if it is
    omitted, then the function's own ._cache attribute, which is created by this
    decorator, will be used.

    This decorator does NOT automatically cache anything - it is up to the
    function to decide what to do with its cache.

    For example:

    >>> @has_cache
    ... def foo(x, cache):
    ...     if x not in cache:
    ...         print("Populating {}".format(x))
    ...         cache[x] = x+1
    ...     return cache[x]
    >>> foo(12)
    Populating 12
    13
    >>> foo(12)
    13
    >>> foo._cache
    {12: 13}
    >>> foo(0)
    Populating 0
    1
    >>> foo(0)
    1
    >>> foo(0, cache={})
    Populating 0
    1

    '''
    fn._cache = {}
    @functools.wraps(fn)
    def newfn(*args, **kwargs):
        if 'cache' not in kwargs:
            kwargs['cache'] = fn._cache
        return fn(*args, **kwargs)
    return newfn
