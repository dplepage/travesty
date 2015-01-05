import sys

if sys.version >= '3': # pragma: no cover
    unicode = str
    basestring = str

import vertigo as vg

from .cantrips.error_aggregator import ErrorAggregator, NestedException

class SingleInvalid(Exception):
    '''A leaf in the nested tree of Invalid exceptions.

    In general, don't raise SingleInvalid directly - instead, raise Invalid

    self.err_id will be a string indicating the specific error, e.g. 'required'
    when a value is missing that shouldn't be, 'not_int' for a value that must
    be an integer but cannot be parsed as one, and so forth. The specific errors
    raised by various Dictifiers are class-specific.

    self.desc is an optional human-readable description of the error. This is
    useful for debugging and for simple applications; for more complex
    applications the best way to generate human-readable strings is via an
    external mapping from err_ids to descriptive strings.

    '''
    def __init__(self, err_id=None, desc=None, **kwargs):
        if kwargs:
            super(SingleInvalid, self).__init__(err_id, kwargs)
        else:
            super(SingleInvalid, self).__init__(err_id)
        self.desc = desc
        self.err_id = err_id
        self.kwargs = kwargs

    def __str__(self):
        bits = [self.err_id, self.desc]
        prefix = u' - '.join(unicode(m) for m in bits if m)
        if self.kwargs:
            return prefix + ' - {}'.format(self.kwargs)
        return prefix

    def id_string(self):
        return self.err_id


class Invalid(NestedException):
    '''Base class for all undictification errors.

    This is a NestedException where the own_errors are all SingleInvalids.
    '''
    def __init__(self, err_id=None, desc=None, **kwargs):
        super(Invalid, self).__init__()
        if err_id or desc or kwargs:
            self.own_errors.append(SingleInvalid(err_id, desc, **kwargs))

    def as_graph(self):
        edges = {k:v.as_graph() for (k,v) in self.sub_errors.items()}
        return vg.PlainGraphNode(self.own_errors, edges)

    def id_string(self):
        n_own = len(self.own_errors)
        n_sub = len(self.sub_errors)
        if n_own+n_sub == 0:
            return "<no message>"
        own = ', '.join(err.id_string() for err in self.own_errors)
        other = ', '.join('{0}: [{1}]'.format(key, err.id_string())
                          for (key, err) in sorted(self.sub_errors.items()))
        return '; '.join(x for x in [own, other] if x)


class InvalidAggregator(ErrorAggregator):
    '''Specialized ErrorAggregator that only aggregates Invalids'''
    error_type = Invalid
    catch_type = Invalid
