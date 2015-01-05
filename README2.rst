=========================
 Travesty: A new Dfiance
=========================

This document contains some partial documentation sketches for pieces of
travesty. I hope to integrate these fragments into the README or other
documentation in the future; in the meantime, they're presented here in case
they might be helpful.

It's all made with doctests, so we need this line::

    >>> import travesty as tv

Dispatchers (dispatcher.py)
===========================

Objects that know what functions to call based on some piece of data. You can
give them arbitrary key functions; for type-dispatch in the style of py3.4's
``singledispatch`` decorator, the key function would be ``lambda x:
type(x).__mro__``.

Apart from being more general than ``singledispatch``, Dispatchers also assume
that they will themselves be passed into the functions they find. This lets
you do some basic inheritance with them, where you define a "recursive"
function that takes a dispatcher and calls it, and then you "inherit from"
that dispatcher, redefining certain cases, without needing to change other
functions.

See ``dispatcher.py`` for some inline docs.


Graphs of Functions
===================

Another idea is to have a graph with a function at each node, with the
convention that each function expects the graph as an argument. The graph is
then basically a pre-built callgraph for the root function, but now you can
swap out pieces of functionality.


Graph Dispatchers and Dispatch Graphs
=====================================

The core of Travesty is the notion of a *dispatch graph*, which is a sort of
hybride of the two ideas above - it's a vertigo graph where each node's value
is a *marker* that indicates how various functions should react to this node.
Alongside dispatch graphs, we have *graph dispatchers*, which are objects that
can choose a function to call based on a marker value.

The two together form a system where you define functions that behave
differently for different marker values, and then you use a graph of marker
values to control the behavior of your functions. For example, let's build a
set of markers and a function on them from scratch.

First, we define our marker types. We're going to make a very simple
arithmetic engine, supporting binary addition and multiplication, so we'll
have three marker types - ``Sum``, ``Prod``, and ``Val``::

    >>> class Sum(tv.Marker): pass
    >>> class Prod(tv.Marker): pass
    >>> class Val(tv.Marker):
    ...     def __init__(self, value):
    ...         self.value = value
    ...     def __repr__(self):
    ...         return "Val({})".format(self.value)

Next, we'll create a dispatcher for our evaluation function::

    >>> eval_graph = tv.make_dispatcher()

Finally, we define the behavior of ``eval_graph`` for different markers::

    >>> @eval_graph.when(Sum)
    ... def eval_sum(dispgraph):
    ...     marker_graph = dispgraph.marker_graph()
    ...     left = eval_graph(marker_graph['a'])
    ...     right = eval_graph(marker_graph['b'])
    ...     return left + right

    >>> @eval_graph.when(Prod)
    ... def eval_prod(dispgraph):
    ...     marker_graph = dispgraph.marker_graph()
    ...     left = eval_graph(marker_graph['a'])
    ...     right = eval_graph(marker_graph['b'])
    ...     return left * right

    >>> @eval_graph.when(Val)
    ... def eval_val(dispgraph):
    ...     return dispgraph.marker.value

Now we can create a graph of markers, and evaluate it::

    >>> import vertigo as vg

We'll express (3 * 2) + (-1 + -3), which equals 2::

    >>> expr = vg.from_dict(dict(
    ...     _self = Sum(),
    ...     a = dict(
    ...         _self = Prod(),
    ...         a = Val(3),
    ...         b = Val(2)
    ...     ),
    ...     b = dict(
    ...         _self = Sum(),
    ...         a = Val(-1),
    ...         b = Val(-3)
    ...     )
    ... ))
    >>> eval_graph(expr)
    2

The cool thing about this is that you can transform the expression by using
normal vertigo manipulation on the graph of markers. For example, we might
replace the 2 with a 4 by changing the value at ``a/b``::

    >>> e2 = vg.overlay(expr, vg.from_flat({'a/b':Val(4)}), reversed=True)
    >>> eval_graph(e2)
    8


Traversers
==========

``travesty`` includes a large collection of ``Marker``s for working with graphs
that describe python objects. It also includes four ``GraphDispatcher``s for
operating on these graphs: ``traverse``, ``validate``, ``dictify``, and
``undictify``. Finally, it has some tools for quickly making graphs about your
own objects.

Suppose we want to make a really simple blogging application. We might define
some classes like so::



    >>> class BlogPost(object):
    ...     '''A single blog post.'''
    ...     def __init__(self, author, text, timestamp=None):
    ...         self.author = author
    ...         self.text = text
    ...         self.timestamp = timestamp or datetime.datetime.now()
    ...
    ...     def __repr__(self):
    ...         return "Post by {} at {}".format(self.author, self.timestamp)
    >>> class Blog(object):
    ...     '''A list of blog posts.'''
    ...     def __init__(self, title, posts=()):
    ...         self.title = title
    ...         self.posts = list(posts)
    ...
    ...     def __repr__(self):
    ...         return "'{}' - {} posts".format(self.title, len(self.posts))

These two classes are pure python - no travesty mixed in. Here's a blog::

    >>> from datetime import datetime, timedelta
    >>> # Generate a datetime for an hour and a day after the above start
    >>> def _time(day, hr):
    ...     return datetime(2014, 1, 15, 00, 00) + timedelta(days=day, hours=hr)

    >>> blog = Blog("The TTB Blog", posts=[
    ...     BlogPost("dplepage", "This is my first post!", _time(0,13)),
    ...     BlogPost("dplepage", "Lorem ipsum, and so forth", _time(1,12)),
    ...     BlogPost("bdarklighter", "I wrote a guest post!", _time(2,14)),
    ... ])


To manipulate these objects using travesty, we're going to need markers for
them. We'll use travesty's ObjectMarker class for this::


    >>> class BlogPostMarker(tv.ObjectMarker):
    ...     target_cls = BlogPost

    >>> class BlogMarker(tv.ObjectMarker):
    ...     target_cls = Blog

Now we can assemble typegraphs for blog posts and blogs::

    >>> blogpost_typegraph = vg.from_dict(dict(
    ...     _self = BlogPostMarker(),
    ...     author = tv.String(),
    ...     text = tv.String(),
    ...     timestamp = tv.DateTime(),
    ... ))

    >>> blog_typegraph = vg.from_dict(dict(
    ...     _self = BlogMarker(),
    ...     title = tv.String(),
    ...     posts = dict(
    ...         _self = tv.List(),
    ...         sub = blogpost_typegraph,
    ...     ),
    ... ))

We can use these to control the four core dispatchers.

Traversal
---------

The ``traverse`` dispatcher creates a vertigo graph from an object::

    >>> print(vg.ascii_tree(tv.traverse(blog_typegraph, blog), sort=True))
    root: 'The TTB Blog' - 3 posts
      +--posts: [Post by dplepage at 2014-01-15 13:00:00, Post by dplepage at 2014-01-16 12:00:00, Post by bdarklighter at 2014-01-17 14:00:00]
      |  +--0: Post by dplepage at 2014-01-15 13:00:00
      |  |  +--author: 'dplepage'
      |  |  +--text: 'This is my first post!'
      |  |  +--timestamp: datetime.datetime(2014, 1, 15, 13, 0)
      |  +--1: Post by dplepage at 2014-01-16 12:00:00
      |  |  +--author: 'dplepage'
      |  |  +--text: 'Lorem ipsum, and so forth'
      |  |  +--timestamp: datetime.datetime(2014, 1, 16, 12, 0)
      |  +--2: Post by bdarklighter at 2014-01-17 14:00:00
      |     +--author: 'bdarklighter'
      |     +--text: 'I wrote a guest post!'
      |     +--timestamp: datetime.datetime(2014, 1, 17, 14, 0)
      +--title: 'The TTB Blog'

Travesty provides ``traverse`` implementations for all of its ``Marker`` types.
In the example above, the ``BlogPostMarker`` and ``BlogMarker`` nodes cause
``traverse`` to visit the items within each object according to the typegraph,
while the ``List`` node causes ``traverse`` to visit each element of the blog's
``.posts`` list.

Validation
----------

The ``validate`` dispatcher walks the structure of an object to test its
validity. Travesty's default implementations of ``validate`` generally only test
that the object is what the typegraph says it should be. If there are problems,
it will raise an ``Invalid`` exception::

    >>> blog.title = None
    >>> tv.validate(blog_typegraph, blog)
    Traceback (most recent call last):
        ...
    Invalid: title: [type_error]

The ``Invalid`` exception is graph-structured, and ``validate`` will evaluate as
much of the tree as possible, collecting all errors it encounters::

    >>> blog.posts[2].timestamp = "Not a date!"
    >>> try:
    ...     tv.validate(blog_typegraph, blog)
    ... except tv.Invalid as e:
    ...     print(vg.ascii_tree(e.as_graph(), sort=True))
    ... else:
    ...     raise Exception("That should have failed.")
    root: []
      +--posts: []
      |  +--2: []
      |     +--timestamp: [SingleInvalid('type_error',)]
      +--title: [SingleInvalid('type_error',)]

In the above case, ``validate`` reported that the title of the blog has the
wrong type (it should have been a string), and so does the timestamp of
``blog.posts[2]`` (it should have been a datetime).

If nothing's wrong, ``validate`` will not return anything - it signals validity
simply by not raising any exceptions::

    >>> blog.posts[2].timestamp = _time(2,14)
    >>> blog.title = "The TTB Blog"
    >>> tv.validate(blog_typegraph, blog)


Serialization
-------------

The ``dictify`` traverser turns python objects into serializable structures::

    >>> blog_dict = tv.dictify(blog_typegraph, blog)
    >>> blog_dict == {
    ...     'posts': [
    ...         {
    ...             'timestamp': u'2014-01-15T13:00:00',
    ...             'text': 'This is my first post!',
    ...             'author': 'dplepage'
    ...         },{
    ...             'timestamp': u'2014-01-16T12:00:00',
    ...             'text': 'Lorem ipsum, and so forth',
    ...             'author': 'dplepage'
    ...         },{
    ...             'timestamp': u'2014-01-17T14:00:00',
    ...             'text': 'I wrote a guest post!',
    ...             'author': 'bdarklighter'
    ...         }],
    ...     'title': 'The TTB Blog',
    ... }
    True

``undictify`` is its inverse::

    >>> b2 = tv.undictify(blog_typegraph, blog_dict)
    >>> b2.title == blog.title
    True
    >>> all(p1.text == p2.text for (p1, p2) in zip(b2.posts,blog.posts))
    True


Shorthand
=========

Writing out the above typegraphs is a lot of extra typing, so Travesty also
provides a helper type ``SchemaObj``. Subclassing ``SchemaObj`` and providing
the ``field_types`` attribute lets your type automatically produce its own
typegraph. Thus, the above examples could have been shortened::

    >>> class BlogPost(tv.SchemaObj):
    ...     '''A single blog post.'''
    ...     field_types = dict(
    ...         author=tv.String(),
    ...         text=tv.String(),
    ...         timestamp=tv.DateTime())
    ...     def __init__(self, author, text, timestamp=None):
    ...         self.author = author
    ...         self.text = text
    ...         self.timestamp = timestamp or datetime.datetime.now()
    ...
    ...     def __repr__(self):
    ...         return "Post by {} at {}".format(self.author, self.timestamp)

    >>> class Blog(tv.SchemaObj):
    ...     '''A list of blog posts.'''
    ...     field_types = dict(
    ...         title = tv.String(),
    ...         posts = tv.List().of(BlogPost))
    ...     def __init__(self, title, posts=()):
    ...         self.title = title
    ...         self.posts = list(posts)
    ...
    ...     def __repr__(self):
    ...         return "'{}' - {} posts".format(self.title, len(self.posts))

    >>> blog = Blog("The TTB Blog", posts=[
    ...     BlogPost("dplepage", "This is my first post!", _time(0,13)),
    ...     BlogPost("dplepage", "Lorem ipsum, and so forth", _time(1,12)),
    ...     BlogPost("bdarklighter", "I wrote a guest post!", _time(2,14)),
    ... ])

The typegraphs and marker types for each are now automatically generated, and
can be accessed by e.g. ``Blog.typegraph`` and ``Blog.marker_cls``.

The first argument to a dispatcher can thus be any of the following:
  1. A typegraph - it will be used directly.
  2. A ``Marker`` instance - it will be wrapped in a graph with no edges
  3. A subclass of the ``Traversable`` class, which has no requirements except
     that you define ``.typegraph`` - ``cls.typegraph`` will be used

``SchemaObj`` subclasses ``Traversable`` and provides automatic typegraph
generation, so ``Blog`` and ``BlogPost`` can be passed directly into the
dispatchers::

    >>> tv.validate(Blog, blog)

Similarly, the entries in the ``field_types`` attr of a SchemaObj can be
typegraphs, markers, or traversables.

