#!/usr/bin/env python3
"""Helper utility for retrieving metadata attributes from a SOLR endpoint"""

import pysolr

__author__ = "Boris Capitanu"
__version__ = "1.0.0"


def get_meta(htrc_id, attributes=None, *, simplify=False, solr_url='http://chinkapin.pti.indiana.edu:9994/solr/meta'):
    """Retrieves volume metadata for a volume referenced by `htrc_id`
    :param htrc_id: The HT id
    :param attributes: The set of attributes to retrieve, or None to retrieve all
    :param simplify: Whether to simplify the objects returned by SOLR; i.e. lists containing one element are replaced
                     with the element
    :param solr_url: The Solr service URL to use
    :return: The metadata object for the volume (or empty if error occurred)
    """
    solr = pysolr.Solr(solr_url, timeout=10)
    fl = {'fl': set(attributes)} if attributes is not None else {}

    results = solr.search('id: %s' % htrc_id.replace(":", "\\:"), **fl)

    if simplify:
        res = []
        for result in results:
            res.append({k: _simplify(v) for k, v in result.items()})
        return res
    else:
        return [result for result in results]


def _simplify(obj):
    """Internal method for simplifying an iterable Python object when it contains a single element
    by returning the element directly
    """
    if type(obj) is not str and hasattr(obj, '__iter__') and len(obj) == 1:
        return obj[0]
    else:
        return obj
