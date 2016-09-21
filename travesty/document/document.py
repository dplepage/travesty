import sys
if sys.version >= '3': # pragma: no cover
    unicode = str

from uuid import uuid4

import vertigo as vg

from travesty import SchemaObj, String, Invalid
from travesty import clone, mutate, traverse, graphize, dictify, undictify
from travesty.base import aggregating_errors, IGNORE
from travesty.cantrips import empty_instance
from travesty.schema import apply_schema
from travesty.object_marker import extract_obj


from .docset import DocSet, DoubleLoadException

def make_uid():
    '''Generate a (probably) unique id.'''
    return unicode(uuid4())

class UnloadedDocumentException(Exception):
    '''Raised on attr access of an unloaded document.'''
    def __init__(self, document, *a, **kw):
        self.document = document
        super(UnloadedDocumentException, self).__init__(document, *a, **kw)

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
        return unicode(self)


clone.default_factory("in_docset", lambda: DocSet())

@clone.when(Document.marker_cls)
def clone_document(dispgraph, doc, **kwargs):
    '''Clone a Document.

    This creates an exact duplicate of the document AND all child documents it
    encounters. However, internally it tracks documents it's already cloned, so
    if the same document appears twice it won't be copied twice.

    If a traverse_docs extras graph is provided, then documents won't be cloned
    except where traverse_docs is True.

    Specify new_uids=True if you want clone to generate new uids for cloned
    documents; specify in_docset=<some DocSet> if you want the cloned documents
    to be added to a docset.

    Note that if you specify new_uids=False and pass in a docset that already
    contains some of these documents, those documents will NOT be cloned
    '''
    new_uids = kwargs.get('new_uids', False)
    docset = kwargs['in_docset']
    # If traverse_docs says not to continue, stop here
    if 'traverse_docs' in dispgraph.extras:
        if not dispgraph.extras.traverse_docs:
            return doc
    # Check type here if needed
    if kwargs.get('error_mode', IGNORE) != IGNORE:
        marker = dispgraph.marker
        if not isinstance(doc, marker.target_cls):
            name = type(doc).__name__
            expected = marker.target_cls.__name__
            msg = "Expected {}, got {}".format(expected, name)
            raise Invalid("type_error", msg)
    uid = make_uid() if new_uids else doc.uid
    key = (type(doc), uid)
    if key in docset:
        return docset[key]
    new_doc = docset.create(type(doc), uid)
    if not doc.loaded:
        # Nothing else to copy if the doc is unloaded
        return new_doc
    # Load a dict of the results of all the child calls
    attrs = extract_obj(dispgraph, doc, kwargs)
    new_doc.load(**attrs)
    return new_doc


# Inherits a default in_docset from clone
@undictify.when(Document.marker_cls)
def udf_document(dispgraph, value, **kwargs):
    error_mode = kwargs.get('error_mode', IGNORE)
    # Check type here if needed
    if error_mode != IGNORE:
        if not isinstance(value, dict):
            name = type(value).__name__
            msg = "Expected dict, got {}".format(name)
            raise Invalid("type_error", msg)
        if 'uid' not in value:
            # TODO standardize the invalid naming pattern
            raise Invalid('missing_key:uid', "Document has no uid.")
    uid = value['uid']
    doctype = dispgraph.marker.target_cls
    in_docset = kwargs['in_docset']
    doc = in_docset.get_or_create(doctype, uid)
    # If the input has no keys besides 'uid', and the doctype expects more, then
    # this is an unloaded document and we should just return it
    if (len(value) == 1) and len(doctype.field_types) > 1:
        return doc
    # Otherwise, we need to populate it.
    with aggregating_errors(error_mode):
        attrs = apply_schema(dispgraph, value, kwargs)
        if error_mode != IGNORE:
            # TODO this duplicates logic in doc.load - should maybe combine?
            extra_keys = set(value.keys()) - set(dispgraph.key_iter())
            if extra_keys:
                raise Invalid('unexpected_fields', keys=extra_keys)
    doc.load(**attrs)
    return doc


mutate.default_factory("_tv_docs_processed", lambda: set())

@mutate.when(Document.marker_cls)
def mutate_document(dispgraph, doc, **kwargs):
    '''Mutate a Document.

    This will only mutate a given Document once, even if said document appears
    multiple times during the recursion.

    As with clone(), you can pass `traverse_docs` to explicitly control when
    this will descend into a given document.
    '''
    docs_processed = kwargs['_tv_docs_processed']
    # If we've already mutated this doc, we're done no matter what.
    if doc in docs_processed:
        return doc
    # If traverse_docs says not to enter this doc, we're also done.
    if 'traverse_docs' in dispgraph.extras:
        if not dispgraph.extras.traverse_docs:
            return doc
    docs_processed.add(doc)
    superdisp = dispgraph.super(Document.marker_cls)
    return superdisp(doc, **kwargs)


dictify.default_factory('_tv_docs_processed', lambda: set())

@dictify.when(Document.marker_cls)
def dictify_document(dispgraph, doc, **kwargs):
    '''Dictify for Document.

    This has the same behavior as clone, except that where clone would create
    a new object, this instead returns a complete serialized object, and where
    clone would return the original object, this instead returns
    dict(uid=doc.uid)
    '''
    docs_processed = kwargs['_tv_docs_processed']
    # If we've already done this doc, just return a stub
    if doc in docs_processed:
        return dict(uid=doc.uid)
    # If traverse_docs says not to enter this doc, just return a stub
    if 'traverse_docs' in dispgraph.extras:
        if not dispgraph.extras.traverse_docs:
            return dict(uid=doc.uid)
    docs_processed.add(doc)
    superdisp = dispgraph.super(Document.marker_cls)
    return superdisp(doc, **kwargs)


graphize.default_factory("_tv_docs_cache", lambda: {})

@graphize.when(Document.marker_cls)
def graphize_document(dispgraph, doc, **kwargs):
    cache = kwargs['_tv_docs_cache']
    if doc in cache:
        # Already done this one
        return cache[doc]
    # Restrict to uid if the doc isn't loaded OR we're not supposed to traverse.
    superdisp = dispgraph.super(Document.marker_cls)
    if not doc.loaded:
        superdisp = superdisp.restrict(['uid'])
    elif 'traverse_docs' in dispgraph.extras:
        if not dispgraph.extras.traverse_docs:
            superdisp = superdisp.restrict(['uid'])
    cache[doc] = vg.PlainGraphNode()
    new = superdisp(doc, **kwargs)
    cache[doc].value = new.value
    cache[doc]._edges = new._edges
    return cache[doc]


traverse.default_factory("_tv_docs_processed", lambda: set())

@traverse.when(Document.marker_cls)
def traverse_document(dispgraph, doc, **kwargs):
    docs_processed = kwargs['_tv_docs_processed']
    # If we've already done this doc, there's nothing to d
    if doc in docs_processed:
        return
    # If we don't traverse here, then we're done
    if 'traverse_docs' in dispgraph.extras:
        if not dispgraph.extras.traverse_docs:
            return
    docs_processed.add(doc)
    superdisp = dispgraph.super(Document.marker_cls)
    # We use getattr so that if you pass a non-document in we won't break until
    # superdisp (which should already handle exceptions)
    if not getattr(doc, 'loaded', False):
        # Unloaded doc: only traverse uid
        return superdisp.restrict(['uid'])(doc, **kwargs)
    # traverse normally
    return superdisp(doc, **kwargs)
