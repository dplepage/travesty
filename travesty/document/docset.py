from travesty import undictify

from .document import DoubleLoadException


class DocSet(object):
    '''Tool for loading linked documents.

    doc_loader.get_or_create(type, uid) returns a document of the given type
    with the given uid.

    doc_loader.load(type, uid, data) works like get_or_create, but loads the
    document from the given data.

    Because the doc_loader keeps only one object for each uid, calling
    get_or_create() twice will return the same object, and more importantly, if
    you call get_or_create() and then later call load() with the same type and
    uid, both will return the same object, and so after calling load() the
    object returned by get_or_create() will now be loaded:

    >>> from travesty import String
    >>> from . import Document
    >>> class Note(Document):
    ...     field_types = dict(content=String())
    >>> docset = DocSet()
    >>> note = docset.get_or_create(Note, 'some_uid')
    >>> note.content
    Traceback (most recent call last):
        ...
    UnloadedDocumentException: <Unloaded Note: some_uid>
    >>> serialized_note = {'uid':'some_uid', 'content':'Lorem ipsum etc.'}
    >>> note2 = docset.load(Note, serialized_note)
    >>> note2.content
    u'Lorem ipsum etc.'
    >>> note.content
    u'Lorem ipsum etc.'
    >>> note is note2
    True

    The undictify implementation for Document can take a DocSets as a
    keyword arg. If the keyword arg 'in_docset' is a DocSet d, then Documents
    will be loaded via d.get_or_create (instead of created unloaded), and will
    be stored in d as they are loaded.

    The helper method docset.load(type, data) is shorthand for
    travesty.undictify(type, data, in_docset=docset)

    '''
    def __init__(self, items=()):
        #: (schema_cls, uid) -> document
        self.document_map = {}
        for item in items:
            self.add(item)

    def add(self, doc):
        key = (type(doc), doc.uid)
        if key in self.document_map:
            raise ValueError("Duplicate uid {1} for type {0}".format(*key))
        self.document_map[key] = doc

    def get(self, type, uid):
        key = (type, uid)
        return self.document_map.get(key, None)

    def create(self, type, uid):
        key = (type, uid)
        if key in self.document_map:
            raise ValueError("Duplicate uid {1} for type {0}".format(*key))
        doc = type._create_unloaded(uid)
        self.document_map[key] = doc
        return doc

    def get_or_create(self, type, uid):
        '''Return a document with the given type and uid

        If this is called multiple times with the same uid, the same document
        will be returned.
        '''
        key = (type, uid)
        doc = self.document_map.setdefault(key, type._create_unloaded(uid))
        assert isinstance(doc, type)
        return doc

    def load(self, type, data, allow_double_load=False, kwargs=None):
        '''Return a loaded document with the given type and uid.

        This returns the same object as a call to get_or_create(type, uid); if
        you call get_or_create and then load, load will return the same object
        but will also populate it with data.

        This is precisely equivalent to

        undictify(type, data, in_docset=self, **kwargs)

        Note that you cannot choose to use a different typegraph or dispatcher
        here - if you need to, just call it directly.
        '''
        if isinstance(data, dict) and 'uid' in data:
            old = self.get(type, data['uid'])
            if old and old.loaded:
                if allow_double_load:
                    return old
                raise DoubleLoadException(type, data['uid'])
        kwargs = kwargs.copy() if kwargs else {}
        kwargs['in_docset'] = self
        return undictify(type, data, **kwargs)

    def __getitem__(self, key):
        return self.document_map[key]

    def __contains__(self, key):
        return key in self.document_map
