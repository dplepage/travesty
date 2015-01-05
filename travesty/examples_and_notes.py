'''

This is a hastily-made set of examples showing travesty, and especially
highlighting what it can do that dfiance can't.

Also it's worth noting that anything in here marked TODO might, in fact, have
already been done - don't assume that TODO means it doesn't exist (but it still
might not)

'''
import datetime
import textwrap

import travesty as tv
from travesty import traverse, validate, dictify, undictify

import vertigo as vg

# TODO reversed=True should be the default for vg.overlay (it makes more sense)
def overlay(*graphs):
    return vg.overlay(*graphs, reversed=True)

# TODO add this helper to vertigo - it's useful
def flat_overlay(graph, flat_dict):
    return overlay(graph, vg.from_flat(flat_dict))



'''
Here's an example using SchemaObj.

It's pretty similar to the one in README2.rst.

'''

class BlogPost(tv.SchemaObj):
    field_types = dict(author=tv.String(), text=tv.String(), timestamp=tv.DateTime())
    def __init__(self, author, text, timestamp=None):
        self.author = author
        self.text = text
        self.timestamp = timestamp or datetime.datetime.now()

    def __repr__(self):
        return "Post by {} at {}".format(self.author, self.timestamp)

class Blog(tv.SchemaObj):
    field_types = dict(
        title = tv.String(),
        posts = tv.List().of(BlogPost))
    def __init__(self, title, posts=()):
        self.title = title
        self.posts = list(posts)

    def __repr__(self):
        return "'{}' - {} posts".format(self.title, len(self.posts))

# 00:00 on Jan 15, 2014
start = datetime.datetime(2014, 1, 15, 00, 00)
# Generate a datetime for an hour and a day after the above start
def _time(day, hr):
    return start + datetime.timedelta(days=day, hours=hr)

# Here's an example blog
blog = Blog("The TTB Blog", posts=[
    BlogPost("dplepage", "This is my first post!", _time(0,13)),
    BlogPost("dplepage", "Lorem ipsum, and so forth and so on.", _time(1,12)),
    BlogPost("bdarklighter", "Meh.", _time(2,14)),
])

# Dictify it!
blog_dict = dictify(Blog, blog)
# we get a nice dict
assert blog_dict == {
    'posts': [
        {
            'author': 'dplepage',
            'text': 'This is my first post!',
            'timestamp': u'2014-01-15T13:00:00',
        },{
            'author': 'dplepage',
            'text': 'Lorem ipsum, and so forth and so on.',
            'timestamp': u'2014-01-16T12:00:00',
        },{
            'author': 'bdarklighter',
            'text': 'Meh.',
            'timestamp': u'2014-01-17T14:00:00',
        }],
    'title': 'The TTB Blog'
}, str(blog_dict)

# undictify gets us our blog back
b2 = undictify(Blog, blog_dict)

assert b2.title == blog.title
assert all(p1.text == p2.text for (p1, p2) in zip(b2.posts,blog.posts))


# traverse wraps the whole thing in a graph
assert vg.ascii_tree(traverse(Blog, blog), sort=True) == '''
root: 'The TTB Blog' - 3 posts
  +--posts: [Post by dplepage at 2014-01-15 13:00:00, Post by dplepage at 2014-01-16 12:00:00, Post by bdarklighter at 2014-01-17 14:00:00]
  |  +--0: Post by dplepage at 2014-01-15 13:00:00
  |  |  +--author: 'dplepage'
  |  |  +--text: 'This is my first post!'
  |  |  +--timestamp: datetime.datetime(2014, 1, 15, 13, 0)
  |  +--1: Post by dplepage at 2014-01-16 12:00:00
  |  |  +--author: 'dplepage'
  |  |  +--text: 'Lorem ipsum, and so forth and so on.'
  |  |  +--timestamp: datetime.datetime(2014, 1, 16, 12, 0)
  |  +--2: Post by bdarklighter at 2014-01-17 14:00:00
  |     +--author: 'bdarklighter'
  |     +--text: 'Meh.'
  |     +--timestamp: datetime.datetime(2014, 1, 17, 14, 0)
  +--title: 'The TTB Blog'
'''.strip()


'''
Typegraph manipulation

Let's make a validation graph that confirms that posts aren't too short.

One way to do this is to actually change the definition of BlogPost to impose
limits on its string, but this means that BlogPost will always have this
restriction, which is not ideal. I recommend that for field_types you try to
stick to just documenting the actual types of things, not validation constraints
that may not always hold.
'''

class LimitedLength(tv.Validator):
    def __init__(self, minlen=None, maxlen=None):
        self.maxlen = maxlen
        self.minlen = minlen

    def validate(self, value, **kwargs):
        if self.maxlen is not None and len(value) > self.maxlen:
            raise tv.Invalid("length/too_long", "Exceeded maximum length of {}".format(self.maxlen))
        if self.minlen is not None and len(value) < self.minlen:
            raise tv.Invalid("length/too_short", "Shorter than minimum length of {}".format(self.minlen))

# Create a new graph that looks just like the blog typegraph but replacing the
# value at posts/sub/text with a Validated wrapper.

g = flat_overlay(Blog.typegraph, {
        'posts/sub/text': tv.Validated(
            Blog.typegraph['posts', 'sub', 'text'].value,
            vdators = [LimitedLength(minlen=5, maxlen=30)],
        )
    }
)

try:
    validate(g, blog)
except tv.Invalid as e:
    # Two of our three posts are too short according to this validation graph:
    tree1 = vg.ascii_tree(e.as_graph(), sort=True)
    tree2 = textwrap.dedent('''
    root: []
      +--posts: []
         +--1: []
         |  +--text: [SingleInvalid('length/too_long',)]
         +--2: []
            +--text: [SingleInvalid('length/too_short',)]
    ''').strip()
    assert tree1 == tree2, tree1
else: # pragma: no cover
    raise RuntimeError("That should have failed.")







'''
Here's a nested type for a calendar. It's a dict with one key, 'events', which
is a list of events. Each event is a dict of (start, end, label, attendees),
where start and end are datetimes, label is a string, and attendees is a list of
strings.

I'm assembling it here with PlainGraphNode.build, so the '_self' keys indicate
values for nodes and all other keys are edges in the graph.

TODO: make some easier ways to write these things out.
'''

calendar_type = vg.PlainGraphNode.build(dict(
    _self = tv.SchemaMapping(),
    events = dict(
        _self = tv.List(), # a calendar is a list of events
        sub = dict(
            _self = tv.SchemaMapping(),
            start = tv.DateTime(),
            end = tv.DateTime(),
            label = tv.String(),
            attendees = dict(
                _self = tv.List(),
                sub = tv.String(),
            ),
        ),
    ),
))

# Update: I added some cooler ways to make these structures. Here's a less
# verbose construction:

calendar_type = tv.SchemaMapping().of(
    events = tv.List().of(
        tv.SchemaMapping().of(
            start = tv.DateTime(),
            end = tv.DateTime(),
            label = tv.String(),
            attendees = tv.List().of(tv.String()),
        ),
    ),
)



'''Here's a small calendar instance.'''

# 00:00 on Jan 15, 2014
start = datetime.datetime(2014, 1, 15, 00, 00)
# Generate a datetime for an hour and a day after the above start
def _time(day, hr):
    return start + datetime.timedelta(days=day, hours=hr)

calendar = dict(events=[
    dict(
        start=_time(0, 14),
        end=_time(0, 15),
        label = "The TTP Project - group meeting",
        attendees = ['Dan', 'Kai'],
    ),
    dict(
        start=_time(1, 11),
        end=_time(1, 12),
        label = "Attack Death Star",
        attendees = ['Biggs Darklighter', 'Wedge Antilles', 'Luke Skywalker', 'Wilhuff Tarkin'],
    ),
    dict(
        start=_time(1, 14),
        end=_time(1, 15),
        label = "Party on Endor",
        attendees = ['Wedge Antilles', 'Luke Skywalker'],
    ),
])



# dictify and undictify take the typegraph as their first args
c_struct = dictify(calendar_type, calendar)
cal2 = undictify(calendar_type, c_struct)
assert cal2 == calendar
# Note that DateTime defaults to a string
assert c_struct['events'][0]['start'] == '2014-01-15T14:00:00'


'''

Now suppose instead of strings we want to output datetimes as dicts with keys
'year', 'month', 'day', 'hour', 'minute', 'second', because we're going to send
our objects to some system that can't parse ISO dates.

There are two different ways to do this: you can change the typegraph to put
your own custom type in, or you use custom dictify/undictify functions to handle
datetimes differently.

Either way, we'll need these two functions:
'''

def datetime_to_dict(value):
    return dict(
        year = value.year,
        month = value.month,
        day = value.day,
        hour = value.hour,
        minute = value.minute,
        second = value.second,
    )

def dict_to_datetime(value):
    return datetime.datetime(
        year = value['year'],
        month = value['month'],
        day = value['day'],
        hour = value['hour'],
        minute = value['minute'],
        second = value['second'],
    )

# Option one: custom type replacement
class DictDateTime(tv.DateTime):
    pass

@dictify.when(DictDateTime)
def dfy_dt(dispgraph, value, **kwargs):
    return datetime_to_dict(value)

@undictify.when(DictDateTime)
def undfy_dt(dispgraph, value, **kwargs):
    return dict_to_datetime(value)

# Create a new typegraph by overlaying a sparse graph on calendar_type
ct2 = flat_overlay(calendar_type, {
    'events/sub/start':DictDateTime(),
    'events/sub/end':DictDateTime(),
})

# The new type markers cause dictify/undictify to use the functions above
c_struct = dictify(ct2, calendar)
cal2 = undictify(ct2, c_struct)
assert cal2 == calendar
# Now the serialized form has a dict
assert c_struct['events'][0]['start'] == dict(
    year=2014,
    month=1,
    day=15,
    hour=14,
    minute=0,
    second=0)



# Option two: custom dispatcher

df2 = dictify.sub()
udf2 = undictify.sub()

# These functions look the same as before, but now we're telling our new dictify
# and undictify functions to handle ALL DateTimes differently.
@df2.when(tv.DateTime)
def dfy_dt2(dispgraph, value, **kwargs):
    return datetime_to_dict(value)

@udf2.when(tv.DateTime)
def undfy_dt2(dispgraph, value, **kwargs):
    return dict_to_datetime(value)

# This has the same behavior as the first case, but this time we didn't have to
# modify the typegraph.

c_struct = df2(calendar_type, calendar)
cal2 = udf2(calendar_type, c_struct)
assert cal2 == calendar
assert c_struct['events'][0]['start'] == dict(
    year=2014,
    month=1,
    day=15,
    hour=14,
    minute=0,
    second=0)





'''
Option 1 is more flexible than 2, because you can e.g. choose to have some dates
dictified one way and some dictified another.

Option 2 is powerful when you want to make sure that you hit ALL dates, instead
of picking and choosing, maybe because picking and choosing is too much work, or
because you're making a general function that could be applied to any typegraph.

'''



