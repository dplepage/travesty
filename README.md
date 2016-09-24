# Travesty: Graph Traversal Dispatchers [![badge](https://travis-ci.org/dplepage/travesty.svg?branch=master)](https://travis-ci.org/dplepage/travesty)

Travesty is a collection of tools for doing function dispatch based on a
[vertigo](https://github.com/dplepage/vertigo) graph.

A lot of these tools are specifically aimed at doing function dispatch based
on a type graph for some object type.

This document uses doctest, so the examples are runnable. We're going to need
vertigo and travesty, and we'll also use the datetime module:

```python

>>> import vertigo as vg
>>> import travesty as tv
>>> import datetime
>>> import pprint

```

## Type Graphs


Travesty defines a bunch of operations that work on *type graphs*. A type graph
is just an ordinary vertigo graph where each node's value is a *type marker*.
For example, suppose you're working with dictionaries about people; each
dictionary has the keys `name`, `birthday`, and `favorites`, where
`name` is a string, `birthday` is a date, and `favorites` is a list of
strings. An example record might look like:

```python

>>> julie = dict(
...     name = "Julie Andrews",
...     birthday = datetime.date(1935, 10, 1),
...     favorites = ["doorbells", "raindrops on roses"]
... )

```

You can describe this structure with a typegraph like so:

```python

>>> typegraph = tv.SchemaMapping().of(
...     name = tv.String(),
...     birthday = tv.Date(),
...     favorites = tv.List().of(tv.String()),
... )
>>> print(vg.ascii_tree(typegraph, sort=True))
root: <SchemaMapping>
  +--birthday: <Date>
  +--favorites: <List>
  |  +--sub: <String>
  +--name: <String>

```

Although this is using shorthands like `.of()`, the end result is a plain
vertigo graph and could easily have been constructed using vertigo tools:

```python

>>> typegraph2 = vg.from_dict(dict(
...     _self = tv.SchemaMapping(),
...     name = tv.String(),
...     birthday = tv.Date(),
...     favorites = dict(
...         _self = tv.List(),
...         sub = tv.String(),
...     ),
... ))
>>> print(vg.ascii_tree(typegraph2, sort=True))
root: <SchemaMapping>
  +--birthday: <Date>
  +--favorites: <List>
  |  +--sub: <String>
  +--name: <String>

```

## Graph Dispatchers

Travesty provides a collection of *graph dispatchers*, which are functions whose
first argument is a graph such as the typegraph above, and which determine what
to do based on the structure of this graph.

For example, the `dictify` graph dispatcher takes two arguments - a typegraph
describing an object, and the object in question - and produces a JSON-
serializable dictionary:

```python

>>> serialized = tv.dictify(typegraph, julie)
>>> serialized == {
...     'birthday': '1935-10-01',
...     'name': 'Julie Andrews',
...     'favorites': ['doorbells', 'raindrops on roses']}
True

```

In this particular example, the only change in the structure is that the
`birthday` field has been serialized to a string (we'll look at more complex
examples later).

The `undictify` dispatcher does the same thing, but in reverse:

```python

>>> tv.undictify(typegraph, serialized) == julie
True

```

The `validate` dispatcher takes a typegraph and an object supposedly matching
that typegraph, and raise an exception if the object doesn't match:

```python

>>> tv.validate(typegraph, julie)
>>> tv.validate(typegraph, dict(
...     name = 'Galactus, Devourer of Worlds',
...     birthday = "Before the dawn of time",
... ))
Traceback (most recent call last):
    ...
Invalid: birthday: [type_error], favorites: [missing_key - Missing key favorites]

```

In this case, validate correctly detected that the `birthday` value of
`"Before the dawn of time"` was not a valid date, and that the `favorites`
key is missing from the entry.


## Custom Types

The most common use-case for travesty is to define new types and get dispatcher
behavior automatically. This is generally done via the `SchemaObj` type, which
automatically constructs a typegraph from a structure you provide:

```python

>>> class Person(tv.SchemaObj):
...     field_types = dict(
...         name = tv.String(),
...         birthday = tv.Date(),
...         favorites = tv.List().of(tv.String())
...     )
...     def __init__(self, name, birthday, favorites=None):
...         self.name = name
...         self.birthday = birthday
...         self.favorites = favorites or []
...
...     def __str__(self):
...         return "{}, born {}".format(self.name, self.birthday)
...
...     def talk(self):
...         if not self.favorites:
...             return "I don't like anything."
...         things = " and ".join(self.favorites)
...         return things + ": These are a few of my favorite things"
...
...     def __eq__(self, other):
...         return all([
...             self.name == other.name,
...             self.birthday == other.birthday,
...             self.favorites == other.favorites
...         ])

```

The items in field_types can be typegraphs or type markers; the call to
`tv.List().of(tv.String())` is shorthand for creating a typegraph with the
list at the root node and the string as the sole child, called `"sub"`.

In almost all respects, `Person` is a normal python class:

```python

>>> things = ["doorbells", "raindrops on roses"]
>>> julie = Person('Julie Andrews', datetime.date(1935, 10, 1), things)
>>> scrooge = Person('Ebenezer Scrooge', datetime.date(1781, 5, 19))
>>> print(julie)
Julie Andrews, born 1935-10-01
>>> print(scrooge)
Ebenezer Scrooge, born 1781-05-19
>>> print(julie.talk())
doorbells and raindrops on roses: These are a few of my favorite things
>>> print(scrooge.talk())
I don't like anything.

```

But, because it inherits from `SchemaObj`, it has a corresponding marker
type and typegraph implied by its `field_types` attribute:

```python

>>> Person.marker_cls
<class 'travesty.schema_obj.PersonMarker'>
>>> print(vg.ascii_tree(Person.typegraph, sort=True))
root: <PersonMarker>
  +--birthday: <Date>
  +--favorites: <List>
  |  +--sub: <String>
  +--name: <String>

```

Consequently, it can already be used as an argument to any of the graph
dispatchers:

```python

>>> serialized = tv.dictify(Person, julie)
>>> serialized == {
...     'name': 'Julie Andrews',
...     'birthday': '1935-10-01',
...     'favorites': ['doorbells', 'raindrops on roses'],
... }
True
>>> julie2 = tv.undictify(Person, serialized)
>>> julie2 == julie
True

```

Note also that most functions that expect typegraphs or marker types will
accept `SchemaObjs` (or indeed any other subclass of `tv.Traversable`),
and will automatically get the type's marker and/or typegraph as needed. Thus
in the above it is sufficient to pass `Person` as the first argument to
`undictify`, rather than passing in `Person.typegraph`.

## Custom Behavior


So far this is all pretty useful, but sometimes you need to do things that
travesty doesn't automatically support. Here are a few ways to customize the
behaviors of things.

### New Markers


You can define your own type markers by subclassing `tv.Marker` and defining
behavior for various dispatchers for your class. This is particularly useful
when you want to create a marker type for a class outside of travesty.

As an example, suppose we have an `EmailAddress` class:


```python

>>> class EmailAddress(object):
...     def __init__(self, name, email):
...         self.name = name
...         self.email = email

```

We can define a marker type for it and corresponding serialization functions
as follows:


```python

>>> class EmailAddrMarker(tv.Marker):
...     pass

>>> from email.utils import parseaddr, formataddr

>>> @tv.undictify.when(EmailAddrMarker)
... def udf_email_addr(d, s, **kw):
...     try:
...         name, email = parseaddr(s)
...     except TypeError:
...         raise tv.Invalid('type_error', 'Unrecognized email: {}'.format(s))
...     return EmailAddress(name, email)

```

Here `EmailAddrMarker` is a type marker that can be used in a typegraph to
indicate an object that should be an `EmailAddress`, and we've defined
behavior for `undictify` for this marker:

```python

>>> e = tv.undictify(EmailAddrMarker(), "Fiona Foonly <fiona@foon.ly>")
>>> print(e.name)
Fiona Foonly
>>> print(e.email)
fiona@foon.ly

```

Dispatchers for which no function is defined will raise an exception:

```python
>>> print(tv.dictify(EmailAddrMarker(), e))
Traceback (most recent call last):
    ...
NotImplementedError: <EmailAddrMarker>

```
We can fix this by making sure to define these:
```python
>>> @tv.dictify.when(EmailAddrMarker)
... def df_email_addr(d, addr, **kw):
...     return formataddr([addr.name, addr.email])

>>> print(tv.dictify(EmailAddrMarker(), e))
Fiona Foonly <fiona@foon.ly>
```

### Dispatcher Inheritance


Travesty's `Dispatcher` class, which is a base class for the graph
dispatchers like `undictify`, supports a form of inheritance, allowing you
to define new dispatchers that include all functionality of existing
dispatchers except where you specifically override it.

For example, the default `dictify` for `tv.Date` is to stringify the date:
```python
>>> datelist_marker = tv.List().of(tv.Date())
>>> datelist = [datetime.date(1815, 12, 10), datetime.date(1882, 3, 23)]
>>> tv.dictify(datelist_marker, datelist)
['1815-12-10', '1882-03-23']
```
This is because many serialization frameworks, such as `json`, do not
support dates by default. However, if you're dictifying objects in order to
serialize them with a data-aware serialization tool like YAML, you might
prefer that dictify and undictify pass dates through unchanged. In this case,
you can define your own dispatchers based on each:
```python
>>> my_dictify = tv.GraphDispatcher([tv.dictify])
>>> my_undictify = tv.GraphDispatcher([tv.undictify])
```
The argument to GraphDispatcher is a list of parents; when operating on a
marker, the dispatcher will check each parent in turn to see if the parent has
behavior for that marker. Thus, as defined above, `my_dictify` and
`my_undictify` are synonyms for `dictify` and `undictify`, respectively.
But now we can add custom behavior to them:
```python
>>> @my_dictify.when(tv.Date)
... @my_undictify.when(tv.Date)
... def passthrough_date(d, date, **kw):
...     return date
```
Now these two functions behave exactly like their parents except when
encountering dates, in which case they pass them through unchanged (note that
the behavior on `tv.List` is unchanged):
```python
>>> my_dictify(datelist_marker, datelist)
[datetime.date(1815, 12, 10), datetime.date(1882, 3, 23)]

>>> my_undictify(datelist_marker, datelist)
[datetime.date(1815, 12, 10), datetime.date(1882, 3, 23)]
```

### Wrappers


`tv.Wrapper` is a marker type for wrapping other marker types. The most
important attribute of a wrapper is its attribute `.marker`, which is the
marker that it wraps, and all dispatchers created by `tv.make_dispatcher`
(as well as all that inherit from those) automatically have a rule for
`Wrapper` that makes them ignore the wrapper and behave as if they'd
encountered the underlying marker.

Consequently, you can transform a typegraph by replacing any marker in the
graph with a wrapper around that marker, and define specific behavior for a
dispatcher when it encounters that marker. All other dispatchers will continue
to work normally on that typegraph, as though the marker weren't there.

For example, suppose you want to require that a date be later than 1900. Then
you might define:
```python
>>> class After1900(tv.Wrapper): pass
>>> @tv.validate.when(After1900)
... def check_1900(d, date, **kw):
...     if date < datetime.date(1900, 1, 1):
...         raise tv.Invalid("date/too_early", "Date must be after 1900")
```
Recall our `Person` typegraph from earlier:
```python
>>> typegraph = Person.typegraph
>>> print(vg.ascii_tree(typegraph, sort=True))
root: <PersonMarker>
  +--birthday: <Date>
  +--favorites: <List>
  |  +--sub: <String>
  +--name: <String>
```
A Person with an early birthday still passes validation:
```python
>>> ramanujan = Person("Srinivasa Ramanujan", datetime.date(1887, 12, 22))
>>> ramanujan.favorites = ["Nested Radicals", "Infinite Series"]
>>> tv.validate(typegraph, ramanujan)
```
If we tweak the typegraph to wrap `birthday` in an `After1900`, validation
will now fail:
```python
>>> overlay = vg.from_flat({'birthday':After1900(typegraph['birthday'].value)})
>>> typegraph2 = vg.overlay(typegraph, overlay, reversed=True)
>>> print(vg.ascii_tree(typegraph2, sort=True))
root: <PersonMarker>
  +--birthday: <After1900(Date)>
  +--favorites: <List>
  |  +--sub: <String>
  +--name: <String>
>>> tv.validate(typegraph2, ramanujan)
Traceback (most recent call last):
    ...
travesty.invalid.Invalid: birthday: [date/too_early - Date must be after 1900]
```
But because other dispatchers ignore wrappers, `dictify` will still work on
the altered typegraph:

```python
>>> tv.dictify(typegraph2, ramanujan) == {
...     'name': 'Srinivasa Ramanujan',
...     'birthday': '1887-12-22',
...     'favorites': ['Nested Radicals', 'Infinite Series'],
... }
True
```

## More Stuff

There are a lot of other cool things you can do with travesty, such as using
the base dispatchers for single-argument type dispatch, or making graph-
scripted algorithms by creating your own markers and dispatchers. Eventually I
hope to add more documentation about these sub-parts. In the meantime, there
are two places you can look for more information.

The first is README2.rst, which contains some bottom-up documentation that I
wrote earlier and that I hope to integrate with this documentation at some
point. The second is `examples_and_notes.py`, which has some quickly thrown-
together examples.
