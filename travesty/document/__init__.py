
'''

>>> from travesty import String, dictify, undictify, traverse, validate, Optional
>>> import vertigo as vg
>>> class Node(Document):
...     # field_types is a fn because python lacks recursive class definitions
...     field_types = lambda cls: dict(
...         name=String(),
...         next=Optional.wrap(cls)
...     )
...     def __init__(self, uid, name, next=None):
...         super(Node, self).__init__(uid)
...         self.name, self.next = name, next
...     def _loaded_repr(self):
...         return "Node({!r}, {!r})".format(self.uid, self.name)
>>> Node._finalize_typegraph()

You can create two nodes that point to each other:

>>> n1 = Node(u"node1", u"First")
>>> n2 = Node(u"node2", u"Second", next=n1)
>>> n1.next = n2

Dictifying without passing in a storage pit behaves just like dictfying a any
other recursive SchemaObj, i.e. it overflows the stack:

>>> dictify(Node, n1)
Traceback (most recent call last):
    ...
RuntimeError: maximum recursion depth exceeded

However, if pass in a dictionary called doc_storage, then dictifying will only
return {'uid':uid}, and the doc_storage dict will be filled with the encountered
documents:

>>> store = {}
>>> dictify(Node, n1, doc_storage=store)
{'uid': u'node1'}
>>> n1_d = store['node1']
>>> n2_d = store['node2']
>>> n1_d == dict(uid='node1', next=dict(uid='node2'), name="First")
True
>>> n2_d == dict(uid='node2', next=dict(uid='node1'), name=u"Second")
True

Then you can undictify them with a DocSet:

>>> loader = DocSet()
>>> node1 = loader.load(Node, n1_d)
>>> node1.name
u'First'

After loading just node1, its next will be an unloaded reference to node2:

>>> node1.next.uid
u'node2'
>>> node1.next.loaded
False
>>> node1.next.name
Traceback (most recent call last):
    ...
UnloadedDocumentException: <Unloaded Node: node2>

But after loading node2, node1.next will be loaded (and will be node2):

>>> node2 = loader.load(Node, n2_d)
>>> node1.next.loaded
True
>>> node1.next.name
u'Second'
>>> node1.next is node2
True
>>> node1.next.next is node1
True

validate and traverse will follow docrefs; be careful not to use them on
recursive structures.

>>> try:
...     validate(Node, node1)
... except RuntimeError as e:
...     assert str(e).startswith("maximum recursion depth exceeded")
... else:
...     raise Exception("That should have failed.")
>>> node2.next = None
>>> validate(Node, node1)
>>> print(vg.ascii_tree(traverse(Node, node1), sort=True))
root: Node(u'node1', u'First')
  +--name: u'First'
  +--next: Node(u'node2', u'Second')
  |  +--name: u'Second'
  |  +--next: None
  |  +--uid: u'node2'
  +--uid: u'node1'



You can also create a DocSet from existing documents, but the DocSet will
NOT automatically search for other referenced documents:

>>> docset = DocSet([node1])
>>> docset[Node, 'node1'] is node1
True
>>> (Node, 'node2') in docset
False
>>> docset.get(Node, 'node2') is None
True

You can add other documents explicitly by calling add:

>>> docset.add(node2)
>>> docset[Node, 'node2'] is node2
True

This will fail if a document with that id is already in the set:

>>> docset.add(node2)
Traceback (most recent call last):
    ...
ValueError: Duplicate uid node2 for type <class 'travesty.document.Node'>

Finally, the explicit DocSet.create(type, uid) function creates an unloaded
document, or fails if that document already exists:

>>> docset.create(Node, 'node3')
<Unloaded Node: node3>
>>> docset.create(Node, 'node1')
Traceback (most recent call last):
    ...
ValueError: Duplicate uid node1 for type <class 'travesty.document.Node'>
'''


from .document import Document, UnloadedDocumentException, DoubleLoadException
from .docset import DocSet

__all__ = ['Document', 'DocSet', 'UnloadedDocumentException',
    'DoubleLoadException']

