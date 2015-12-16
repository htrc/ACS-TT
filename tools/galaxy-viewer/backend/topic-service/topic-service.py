#!/usr/bin/env python3
"""Galaxy Viewer topic service API

This is the backend service that supports the Galaxy Viewer frontend by providing
a set of API calls for retrieving required data from the associated MongoDB database.

"""

from bottle import Bottle, request, response, abort
from bottle_mongo import MongoPlugin
from bson import ObjectId
from collections import defaultdict, Counter, OrderedDict
from operator import itemgetter

__author__ = "Boris Capitanu"
__version__ = "1.0.0"


class EnableCors(object):
    """BottlePy plugin for enabling CORS"""
    name = 'enable_cors'
    api = 2

    def apply(self, fn, context):
        def _enable_cors(*args, **kwargs):
            # set CORS headers
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, ' \
                                                               'X-Requested-With, X-CSRF-Token'

            if request.method != 'OPTIONS':
                # actual request; reply with the actual response
                return fn(*args, **kwargs)

        return _enable_cors


app = Bottle()
app.install(EnableCors())


def jsonp(dictionary):
    """Enable JSONP call wrapping for result data in the given dictionary

    :param dictionary: The result data to wrap
    :return: A JSONP wrapper
    """
    callback = request.query.callback
    if callback:
        return '{}({})'.format(callback, dictionary)
    else:
        return dictionary


@app.route('/datasets', method='GET')
def get_datasets(mongodb):
    """Retrieves metadata about each dataset stored in the given instance of MongoDB

    :param mongodb: The mongodb instance
    :return: The datasets
    """
    datasets = []
    for dataset in mongodb['datasets'].find({}, {'name': 1}):
        dataset['id'] = str(dataset.pop('_id'))
        datasets.append(dataset)

    return jsonp({'datasets': datasets})


@app.route('/datasets/<dataset_id>/topics/data', method='GET')
def get_topics_data(dataset_id, mongodb):
    """Convenience method for retrieving a number of attributes in 'bulk'

    :param dataset_id: The dataset ID to query
    :param mongodb: The mongodb instance
    :return: The requested attribute values
    """
    meta_vars = request.query.content or None

    if meta_vars is None:
        abort(400, "Missing '&content=' request argument")

    valid_vars = {'mean', 'trend', 'alpha', 'first_word', 'topic_dist', 'center_dist'}

    data = defaultdict(list)
    meta_vars = set(meta_vars.split(','))

    for var in meta_vars:
        if var not in valid_vars:
            abort(400, "Unsupported content requested: {}. Valid options are: {}".format(var, ', '.join(valid_vars)))

    projection = {}
    if 'mean' in meta_vars: projection['mean'] = 1
    if 'trend' in meta_vars: projection['trend'] = 1
    if 'alpha' in meta_vars: projection['alpha'] = 1
    if 'first_word' in meta_vars: projection['keywords'] = 1

    if len(projection) > 0:
        projection['_id'] = False
        topics = mongodb['topics'].find({'datasetId': ObjectId(dataset_id)}, projection)
        for row in topics:
            for var in meta_vars:
                if var == 'mean':
                    data['mean'].append(row['mean'])
                elif var == 'trend':
                    data['trend'].append(row['trend'])
                elif var == 'alpha':
                    data['alpha'].append(row['alpha'])
                elif var == 'first_word':
                    data['first_word'].append(row['keywords'][0])

    projection = {}
    if 'topic_dist' in meta_vars: projection['distances'] = 1
    if 'center_dist' in meta_vars: projection['centerDist'] = 1

    if len(projection) > 0:
        projection['_id'] = False
        datasets = mongodb['datasets'].find_one({'_id': ObjectId(dataset_id)}, projection)

        if datasets is None:
            abort(404, "Unknown dataset id: {}".format(dataset_id))

        for var in meta_vars:
            if var == 'topic_dist':
                data['topic_dist'] = datasets['distances']
            elif var == 'center_dist':
                data['center_dist'] = datasets['centerDist']

    return jsonp(data)


@app.route('/datasets/<dataset_id>/topics/topic_distances', method='GET')
def get_topic_distances(dataset_id, mongodb):
    """Retrieves inter-topic distances

    :param dataset_id: The dataset ID to query
    :param mongodb: The mongodb instance
    :return: The inter-topic distances as a upper-triangular matrix encoded as a vector
    """
    datasets = mongodb['datasets'].find_one({'_id': ObjectId(dataset_id)},
                                            {'_id': False, 'distances': 1})
    if datasets is None:
        abort(404, "Unknown dataset id: {}".format(dataset_id))

    topic_distances = datasets['distances']

    return jsonp({'topic_dist': topic_distances})


@app.route('/datasets/<dataset_id>/topics/center_distances', method='GET')
def get_topic_center_distances(dataset_id, mongodb):
    """Retrieves the distances of the topics from 'center'

    :param dataset_id: The dataset ID to query
    :param mongodb: The mongodb instance
    :return: The topic center distances
    """
    datasets = mongodb['datasets'].find_one({'_id': ObjectId(dataset_id)},
                                            {'_id': False, 'centerDist': 1})
    if datasets is None:
        abort(404, "Unknown dataset id: {}".format(dataset_id))

    center_distances = datasets['centerDist']

    return jsonp({'center_dist': center_distances})


@app.route('/datasets/<dataset_id>/token_counts_by_year', method='GET')
def get_corpus_token_counts_by_year(dataset_id, mongodb):
    """Retrieves the token counts by year at the corpus level

    :param dataset_id: The dataset ID to query
    :param mongodb: The mongodb instance
    :return: The corpus-level token counts by year
    """
    datasets = mongodb['datasets'].find_one({'_id': ObjectId(dataset_id)},
                                            {'_id': False, 'documents': 1})
    if datasets is None:
        abort(404, "Unknown dataset id: {}".format(dataset_id))

    documents = datasets['documents']

    state_docs = mongodb['state'].find({'datasetId': ObjectId(dataset_id)},
                                       {'_id': False})
    if state_docs is None:
        abort(404, "Unknown dataset id: {}".format(dataset_id))

    years = defaultdict(Counter)

    for doc in state_docs:
        publish_date = documents[doc['docId']]['publishDate']
        year = publish_date.year if publish_date is not None else -1  # a bit ugly, but None breaks sorted(...)
        doc_token_counts = zip(doc['tokens'], doc['counts'])
        topic_token_counts = Counter(dict(doc_token_counts))
        years[year].update(topic_token_counts)

    token_counts_by_year = OrderedDict(sorted([(y, sum(c.values())) for y, c in years.items()], key=itemgetter(0)))

    return jsonp(token_counts_by_year)


@app.route('/datasets/<dataset_id>/doc_counts_by_year', method='GET')
def get_corpus_doc_counts_by_year(dataset_id, mongodb):
    """Retrieves the corpus-level document counts by year

    :param dataset_id: The dataset ID to query
    :param mongodb: The mongodb instance
    :return: The corpus-level documents counts by year
    """
    datasets = mongodb['datasets'].find_one({'_id': ObjectId(dataset_id)},
                                            {'_id': False, 'documents': 1})
    if datasets is None:
        abort(404, "Unknown dataset id: {}".format(dataset_id))

    documents = datasets['documents']

    years = Counter()

    for doc in documents:
        publish_date = doc['publishDate']
        year = publish_date.year if publish_date is not None else -1  # a bit ugly, but None breaks sorted(...)
        years[year] += 1

    doc_counts_by_year = OrderedDict(sorted([(y, c) for y, c in years.items()], key=itemgetter(0)))

    return jsonp(doc_counts_by_year)


@app.route('/datasets/<dataset_id>/topics/<topic_id:int>/token_counts', method='GET')
def get_topic_token_counts(dataset_id, topic_id, mongodb):
    """Retrieves the token counts for the given topic_id

    :param dataset_id: The dataset ID to query
    :param topic_id: The topic ID
    :param mongodb: The mongodb instance
    :return: The token counts
    """
    datasets = mongodb['datasets'].find_one({'_id': ObjectId(dataset_id)},
                                            {'_id': False, 'tokens': 1})
    if datasets is None:
        abort(404, "Unknown dataset id: {}".format(dataset_id))

    token_map = {t['id']: t['token'] for t in datasets['tokens']}

    topics = mongodb['topics'].find_one({'datasetId': ObjectId(dataset_id), 'topicId': topic_id},
                                        {'_id': False, 'keywords': 1})
    if topics is None:
        abort(404, "Unknown topic id: {}".format(topic_id))

    state_docs = mongodb['state'].find({'datasetId': ObjectId(dataset_id), 'topicId': topic_id},
                                       {'_id': False})

    topic_keywords = topics['keywords']

    token_counts = Counter()
    for doc in state_docs:
        tokens = [token_map[tid] for tid in doc['tokens']]
        doc_token_counts = Counter(dict(zip(tokens, doc['counts'])))
        token_counts.update(doc_token_counts)

    token_counts = [[word, token_counts[word]] for word in topic_keywords]

    return jsonp({'token_counts': token_counts})


@app.route('/datasets/<dataset_id>/topics/<topic_id:int>/doc_prominence', method='GET')
def get_topic_doc_prominence(dataset_id, topic_id, mongodb):
    """Retrieves the topic-level document prominence for a given topic_id

    :param dataset_id: The dataset ID to query
    :param topic_id: The topic ID
    :param mongodb: The mongodb instance
    :return: The document prominence values for each document for the given topic_id
    """
    datasets = mongodb['datasets'].find_one({'_id': ObjectId(dataset_id)},
                                            {'_id': False, 'documents': 1})
    if datasets is None:
        abort(404, "Unknown dataset id: {}".format(dataset_id))

    documents = datasets['documents']

    topics = mongodb['topics'].find_one({'datasetId': ObjectId(dataset_id), 'topicId': topic_id},
                                        {'_id': False, 'docAllocation': 1})
    if topics is None:
        abort(404, "Unknown topic id: {}".format(topic_id))

    topic_alloc_per_doc = list(enumerate(topics['docAllocation']))
    max_results = request.query.limit or None
    if max_results is not None:
        max_results = int(max_results)

    counter = Counter(dict(topic_alloc_per_doc))

    result = []
    for doc_id, prominence in counter.most_common(n=max_results):
        doc = documents[doc_id]
        doc['prominence'] = prominence
        publish_date = doc['publishDate']
        doc['publishDate'] = publish_date.isoformat() if publish_date is not None else None
        if 'volid' not in doc:
            doc['volid'] = str(doc_id)
        result.append(doc)

    return jsonp({'doc_prominence': result})


@app.route('/datasets/<dataset_id>/topics/<topic_id:int>/token_counts_by_year', method='GET')
def get_topic_token_counts_by_year(dataset_id, topic_id, mongodb):
    """Retrieves the topic-level token counts by year for the given topic_id

    :param dataset_id: The dataset ID to query
    :param topic_id: The topic ID
    :param mongodb: The mongodb instance
    :return: The topic-level token counts by year for the given topic_id
    """
    datasets = mongodb['datasets'].find_one({'_id': ObjectId(dataset_id)},
                                            {'_id': False, 'documents': 1, 'tokens': 1})
    if datasets is None:
        abort(404, "Unknown dataset id: {}".format(dataset_id))

    documents = datasets['documents']
    token_map = {t['id']: t['token'] for t in datasets['tokens']}

    topics = mongodb['topics'].find_one({'datasetId': ObjectId(dataset_id), 'topicId': topic_id},
                                        {'_id': False, 'keywords': 1})
    if topics is None:
        abort(404, "Unknown topic id: {}".format(topic_id))

    state_docs = mongodb['state'].find({'datasetId': ObjectId(dataset_id), 'topicId': topic_id},
                                       {'_id': False})

    topic_keywords = set(topics['keywords'])

    years = defaultdict(Counter)
    for doc in state_docs:
        publish_date = documents[doc['docId']]['publishDate']
        year = publish_date.year if publish_date is not None else None
        tokens = [token_map[tid] for tid in doc['tokens']]
        doc_token_counts = zip(tokens, doc['counts'])
        topic_token_counts = Counter({t: c for t, c in doc_token_counts if t in topic_keywords})
        years[year].update(topic_token_counts)

    return jsonp(years)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
            description="Galaxy Viewer topic service API backend",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--host', metavar='host', dest='host', default='localhost',
                        help="Hostname or IP address for the service to bind to")
    parser.add_argument('--port', metavar='port', dest='port', type=int, default=8080,
                        help="Port number to listen on")
    parser.add_argument('--db-host', metavar='host', dest='db_host', default='localhost',
                        help="The hostname or IP address of the MongoDB server to connect to")
    parser.add_argument('--db', metavar='name', dest='db_name', default='galaxyviewer',
                        help="The name of the database containing the GalaxyViewer data")
    parser.add_argument('--debug', dest='debug', action='store_true',
                        help="Enable debug mode")
    args = parser.parse_args()

    mongo_plugin = MongoPlugin(uri='mongodb://%s' % args.db_host, db=args.db_name, json_mongo=True)

    app.install(mongo_plugin)
    app.run(host=args.host, port=args.port, debug=args.debug)
