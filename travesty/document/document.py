import sys
if sys.version >= '3': # pragma: no cover
    unicode = str
    basestring = str

from uuid import uuid4

from travesty import SchemaObj, String, Invalid, InvalidAggregator, ObjectMarker
from travesty import dictify, undictify, validate, traverse
from travesty.cantrips import empty_instance

def make_uid():
    '''Generate a (probably) unique id.'''
    return unicode(uuid4())

class UnloadedDocumentException(Exception):
    '''Raised on attr access of an unloaded document.'''
    def __init__(self, document, *a, **kw):
        self.document = document
        super(UnloadedDocumentException, self).__init__(document, *a, **kw)

class DoubleLoadException(Exception):
    '''Raised if a loaded document is loaded again.'''
    pass

class Document(SchemaObj):
    '''Document protocol for non-tree object graphs.

    Every document has a uid, which is a string. Each document is assumed to
    have a tree-like typegraph, but documents can contain references to other
    documents (or even to themselves), and this reference structure not be

    Every document has a uid; subclasses determine what other data they have.

    A Document object can be either loaded or unloaded; the doc.loaded flag
    indicates which a particular one is. A loaded document has data, and behaves
    normally; an unloaded document is a placeholder for a document that is
    stored in some external data store (such as a database) but has not had its
    data loaded.

    An unloaded Document has loaded=False; its uid is set but all the other
    attributes defined by field_types are missing, and trying to access them
    will raise an UnloadedDocumentException.

    In general you will never need to create unloaded documents directly, but
    the undictifier (see below) sometimes will.

    If no uid is provided during initialization, then the Document is given a
    generated uid and has new=True.
    '''
    field_types = dict(
        uid = String(),
    )
    loaded = False

    def __init__(self, uid=None, **attrs):
        self.loaded = True
        super(Document, self).__init__()
        # If uid is not specified, generate one randomly
        if uid is None:
            uid = make_uid()
        self.uid = uid
        self._load(**attrs)

    @classmethod
    def _create_unloaded(cls, uid):
        '''Create an unloaded instance of this class.'''
        return empty_instance.create_instance(cls, dict(
            loaded = False,
            uid = uid,
        ))

    def load(self, **attrs):
        if self.loaded:
            raise DoubleLoadException(type(self), self.uid)
        self._load(**attrs)
        return self

    def _load(self, **attrs):
        '''Load an unloaded instance of this class'''
        self.loaded = True
        extras = set(attrs.keys()) - set(self.field_types.keys())
        if extras:
            keylist = ', '.join('"{}"'.format(k) for k in extras)
            msg = "{0}() got an unexpected keyword arguments {1}"
            msg = msg.format(type(self).__name__, keylist)
            raise TypeError(msg)
        for key in self.field_types.keys():
            if key == 'uid': continue
            setattr(self, key, attrs.get(key, None))
        return self

    def __getattr__(self, attr):
        '''Raise UnloadedDocumentException on access to unloaded attributes'''
        if not self.loaded and attr != 'uid' and attr in self.field_types:
            raise UnloadedDocumentException(self)
        return object.__getattribute__(self, attr)

    def _loaded_str(self):
        '''__str__ for loaded instances.

        Subclassess can override this to specify __str__ behavior for loaded
        instances while preserving the default for unloaded instances.
        '''
        return "<{}: {}>".format(type(self).__name__, self.uid)

    def __str__(self):
        if self.loaded:
            return self._loaded_str()
        return "<Unloaded {}: {}>".format(type(self).__name__, self.uid)

    def _loaded_repr(self):
        '''__repr__ for loaded instances.

        Subclassess can override this to specify __repr__ behavior for loaded
        instances while preserving the default for unloaded instances.
        '''
        return "<{}: {}>".format(type(self).__name__, self.uid)

    def __repr__(self):
        if self.loaded:
            return self._loaded_repr()
        return str(self)


@dictify.when(Document.marker_cls)
def df_document(dispgraph, doc, doc_storage=None, no_doc_kids=False, **kwargs):
    '''Dictify a document.

    The behavior is different depending on whether doc_storage kwarg is None.

    If it is, then this behaves just like dictifying a SchemaObj - the document
    is serialized to a dictionary, which is returned.

    If doc_storage is not None, then it should be a dictionary mapping uids to
    serialized Documents. In this case, this function will always return
    {'uid':doc.uid}, but if doc.uid isn't already in doc_storage then the
    serialized dictionary of this object will be added to it as a side effect.

    Thus, if you have a complex structure of Documents, dictifying the root with
    no doc_storage may give you multiple serialized copies of the same object,
    while serializing with doc_storage={} will populate doc_storage with
    serialized versions of each object, leaving only {'uid':<uid>} where
    sub-documents are present.

    '''
    # unloaded doc -> {"uid":doc.uid}
    if not doc.loaded or no_doc_kids == "internal":
        return dict(uid=doc.uid)
    # doc already stored -> {"uid": doc.uid}
    if doc_storage is not None and doc.uid in doc_storage:
        return dict(uid=doc.uid)
    if doc_storage is not None: # place a marker in here in case of recursion
        doc_storage[doc.uid] = dict(uid=doc.uid)
    superdisp = dispgraph.super(Document.marker_cls)
    if no_doc_kids:
        no_doc_kids = "internal"
    result = superdisp(doc, doc_storage=doc_storage, no_doc_kids=no_doc_kids, **kwargs)
    if doc_storage is not None:
        # When using storage, always return just {'uid':doc.uid}
        doc_storage[doc.uid] = result
        return dict(uid=doc.uid)
    # without storage, return full result
    return result


@undictify.when(Document.marker_cls)
def udf_document(dispgraph, value, in_docset=None, **kwargs):
    if not isinstance(value, dict):
        raise Invalid('type_error', "Expected dict, got {}".format(type(value)))
    if 'uid' not in value:
        raise Invalid('missing_key:uid', "Document has no uid.")
    uid = value['uid']
    doctype = dispgraph.marker.target_cls
    if in_docset is not None:
        doc = in_docset.get_or_create(doctype, uid)
    else:
        doc = doctype._create_unloaded(uid)
    # If the input has no keys besides 'uid', and the doctype expects more, then
    # this is an unloaded document and we should just return it
    if (len(value) == 1) and len(doctype.field_types) > 1:
        return doc
    # Otherwise, we need to populate it.
    error_agg = InvalidAggregator(autoraise = kwargs.get('fail_early', False))
    with error_agg.checking():
        # Need to jump over ObjectMarker and go straight to Schema so we get a
        # dictionary back
        # TODO could probably refactor ObjectMarker and/or Schema to avoid this
        result = dispgraph.super(ObjectMarker)(value, in_docset=in_docset, **kwargs)
    extra_keys = set(value.keys()) - set(dispgraph.key_iter())
    if extra_keys:
        error_agg.own_error(Invalid('unexpected_fields', keys=extra_keys))
    error_agg.raise_if_any()
    doc.load(**result)
    return doc

@validate.when(Document.marker_cls)
def vd_document(dispgraph, doc, no_doc_kids=False, **kwargs):
    doctype = dispgraph.marker.target_cls
    if not isinstance(doc, doctype):
        raise Invalid("type_error", "Expected {}, got {}".format(doctype, type(doc)))
    # This actually works, amusingly enough
    traverse_document(dispgraph, doc, no_doc_kids=no_doc_kids, **kwargs)

@traverse.when(Document.marker_cls)
def traverse_document(dispgraph, doc, zipgraph=None, no_doc_kids=False, **kwargs):
    superdisp = dispgraph.super(Document.marker_cls)
    if not doc.loaded or no_doc_kids == "internal":
        # Unloaded doc: only traverse uid
        return superdisp.restrict(['uid'])(doc, zipgraph=zipgraph, no_doc_kids=no_doc_kids, **kwargs)
    if no_doc_kids:
        no_doc_kids = "internal"
    # Treat loaded docs like any other SchemaObj
    return superdisp(doc, zipgraph=zipgraph, no_doc_kids=no_doc_kids, **kwargs)
