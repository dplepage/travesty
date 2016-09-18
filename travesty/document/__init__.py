
'''

>>> from travesty import String, Optional
>>> from travesty import dictify, undictify, traverse, validate, graphize
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

Dictify will only serialize any given document once - when there are multiple
occurences of the same document, all the other occurrences will serialize just
to {'uid':doc.uid}. This means you can dictify recursive objects:

>>> s = dictify(Node, n1)
>>> s == {
... 'uid': 'node1',
... 'name': 'First',
... 'next': {
...     'uid': 'node2',
...     'name': 'Second',
...     'next': {'uid': 'node1'}
... }}
True


>>> validate(Node, n1)
>>> n2.next = None
>>> validate(Node, n1) # but now it won't.
>>> print(vg.ascii_tree(graphize(Node, n1), sort=True))
root: Node(u'node1', u'First')
  +--name: u'First'
  +--next: Node(u'node2', u'Second')
  |  +--name: u'Second'
  |  +--next: None
  |  +--uid: u'node2'
  +--uid: u'node1'



You can also create a DocSet from existing documents, but the DocSet will
NOT automatically search for other referenced documents:

>>> docset = DocSet([n1])
>>> docset[Node, 'node1'] is n1
True
>>> (Node, 'node2') in docset
False
>>> docset.get(Node, 'node2') is None
True

You can add other documents explicitly by calling add:

>>> docset.add(n2)
>>> docset[Node, 'node2'] is n2
True

This will fail if a document with that id is already in the set:

>>> docset.add(n2)
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

