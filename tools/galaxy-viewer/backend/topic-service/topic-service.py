from bottle import Bottle, request, response, abort
from bottle_mongo import MongoPlugin
from bson import ObjectId
from collections import defaultdict, Counter, OrderedDict
from operator import itemgetter


class EnableCors(object):
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


mongo_plugin = MongoPlugin(uri='mongodb://127.0.0.1', db='galaxyviewer', json_mongo=True)

app = Bottle()
app.install(mongo_plugin)
app.install(EnableCors())


def jsonp(dictionary):
    callback = request.query.callback
    if callback:
        return '{}({})'.format(callback, dictionary)
    else:
        return dictionary


@app.route('/datasets', method='GET')
def get_datasets(mongodb):
    datasets = []
    for dataset in mongodb['datasets'].find({}, {'name': 1}):
        dataset['id'] = str(dataset.pop('_id'))
        datasets.append(dataset)

    return jsonp({'datasets': datasets})


@app.route('/datasets/<dataset_id>/topics/data', method='GET')
def get_topics_data(dataset_id, mongodb):
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
        q = mongodb['topics'].find({'datasetId': ObjectId(dataset_id)}, projection)
        for row in q:
            for var in meta_vars:
                if var == 'mean': data['mean'].append(row['mean'])
                elif var == 'trend': data['trend'].append(row['trend'])
                elif var == 'alpha': data['alpha'].append(row['alpha'])
                elif var == 'first_word': data['first_word'].append(row['keywords'][0])

    projection = {}
    if 'topic_dist' in meta_vars: projection['distances'] = 1
    if 'center_dist' in meta_vars: projection['centerDist'] = 1

    if len(projection) > 0:
        projection['_id'] = False
        q = mongodb['datasets'].find_one({'_id': ObjectId(dataset_id)}, projection)

        if q is None:
            abort(404, "Unknown dataset id: {}".format(dataset_id))

        for var in meta_vars:
            if var == 'topic_dist': data['topic_dist'] = q['distances']
            elif var == 'center_dist': data['center_dist'] = q['centerDist']

    return jsonp(data)


@app.route('/datasets/<dataset_id>/topics/topic_distances', method='GET')
def get_topic_distances(dataset_id, mongodb):
    q = mongodb['datasets'].find_one({'_id': ObjectId(dataset_id)},
                                     {'_id': False, 'distances': 1})
    if q is None:
        abort(404, "Unknown dataset id: {}".format(dataset_id))

    topic_distances = q['distances']

    return jsonp({'topic_dist': topic_distances})


@app.route('/datasets/<dataset_id>/topics/center_distances', method='GET')
def get_topic_center_distances(dataset_id, mongodb):
    q = mongodb['datasets'].find_one({'_id': ObjectId(dataset_id)},
                                     {'_id': False, 'centerDist': 1})
    if q is None:
        abort(404, "Unknown dataset id: {}".format(dataset_id))

    center_distances = q['centerDist']

    return jsonp({'center_dist': center_distances})


@app.route('/datasets/<dataset_id>/token_counts_by_year', method='GET')
def get_corpus_token_counts_by_year(dataset_id, mongodb):
    q = mongodb['datasets'].find_one({'_id': ObjectId(dataset_id)},
                                     {'_id': False, 'documents': 1})
    if q is None:
        abort(404, "Unknown dataset id: {}".format(dataset_id))

    documents = q['documents']

    q = mongodb['topics'].find({'datasetId': ObjectId(dataset_id)},
                               {'_id': False, 'documents': 1})
    if q is None:
        abort(404, "Unknown dataset id: {}".format(dataset_id))

    years = defaultdict(Counter)

    for topic in q:
        for doc in topic['documents']:
            publish_date = documents[doc['id']]['publishDate']
            year = publish_date.year if publish_date is not None else None
            doc_token_counts = zip(doc['tokens'], doc['counts'])
            topic_token_counts = Counter(dict(doc_token_counts))
            years[year].update(topic_token_counts)

    token_counts_by_year = OrderedDict(sorted([(y, sum(c.values())) for y, c in years.items()], key=itemgetter(0)))

    return jsonp(token_counts_by_year)


@app.route('/datasets/<dataset_id>/doc_counts_by_year', method='GET')
def get_corpus_doc_counts_by_year(dataset_id, mongodb):
    q = mongodb['datasets'].find_one({'_id': ObjectId(dataset_id)},
                                     {'_id': False, 'documents': 1})
    if q is None:
        abort(404, "Unknown dataset id: {}".format(dataset_id))

    documents = q['documents']

    years = Counter()

    for doc in documents:
        publish_date = doc['publishDate']
        year = publish_date.year if publish_date is not None else None
        years[year] += 1

    doc_counts_by_year = OrderedDict(sorted([(y, c) for y, c in years.items()], key=itemgetter(0)))

    return jsonp(doc_counts_by_year)


@app.route('/datasets/<dataset_id>/topics/<topic_id:int>/token_counts', method='GET')
def get_topic_token_counts(dataset_id, topic_id, mongodb):
    q = mongodb['datasets'].find_one({'_id': ObjectId(dataset_id)},
                                     {'_id': False, 'tokens': 1})
    if q is None:
        abort(404, "Unknown dataset id: {}".format(dataset_id))

    token_map = {t['id']: t['token'] for t in q['tokens']}

    q = mongodb['topics'].find_one({'datasetId': ObjectId(dataset_id), 'topicId': topic_id},
                                   {'_id': False, 'documents': 1, 'keywords': 1})
    if q is None:
        abort(404, "Unknown topic id: {}".format(topic_id))

    topic_documents = q['documents']
    topic_keywords = q['keywords']

    token_counts = Counter()
    for doc in topic_documents:
        tokens = [token_map[tid] for tid in doc['tokens']]
        doc_token_counts = Counter(dict(zip(tokens, doc['counts'])))
        token_counts.update(doc_token_counts)

    token_counts = [[word, token_counts[word]] for word in topic_keywords]

    return jsonp({'token_counts': token_counts})


@app.route('/datasets/<dataset_id>/topics/<topic_id:int>/doc_prominence', method='GET')
def get_topic_doc_prominence(dataset_id, topic_id, mongodb):
    q = mongodb['datasets'].find_one({'_id': ObjectId(dataset_id)},
                                     {'_id': False, 'documents': 1})
    if q is None:
        abort(404, "Unknown dataset id: {}".format(dataset_id))

    documents = q['documents']

    q = mongodb['topics'].find_one({'datasetId': ObjectId(dataset_id), 'topicId': topic_id},
                                   {'_id': False, 'docAllocation': 1})
    if q is None:
        abort(404, "Unknown topic id: {}".format(topic_id))

    topic_alloc_per_doc = list(enumerate(q['docAllocation']))
    max_results = request.query.limit or None
    if max_results is not None:
        max_results = int(max_results)

    counter = Counter(dict(topic_alloc_per_doc))

    result = []
    for doc_id, prominence in counter.most_common(n=max_results):
        doc = documents[doc_id]
        doc['prominence'] = prominence
        doc['publishDate'] = doc['publishDate'].isoformat()
        if 'volid' not in doc:
            doc['volid'] = str(doc_id)
        result.append(doc)

    return jsonp({'doc_prominence': result})


@app.route('/datasets/<dataset_id>/topics/<topic_id:int>/token_counts_by_year', method='GET')
def get_topic_token_counts_by_year(dataset_id, topic_id, mongodb):
    q = mongodb['datasets'].find_one({'_id': ObjectId(dataset_id)},
                                     {'_id': False, 'documents': 1, 'tokens': 1})
    if q is None:
        abort(404, "Unknown dataset id: {}".format(dataset_id))

    documents = q['documents']
    token_map = {t['id']: t['token'] for t in q['tokens']}

    q = mongodb['topics'].find_one({'datasetId': ObjectId(dataset_id), 'topicId': topic_id},
                                   {'_id': False, 'documents': 1, 'keywords': 1})
    if q is None:
        abort(404, "Unknown topic id: {}".format(topic_id))

    topic_documents = q['documents']
    topic_keywords = set(q['keywords'])

    years = defaultdict(Counter)
    for doc in topic_documents:
        publish_date = documents[doc['id']]['publishDate']
        year = publish_date.year if publish_date is not None else None
        tokens = [token_map[tid] for tid in doc['tokens']]
        doc_token_counts = zip(tokens, doc['counts'])
        topic_token_counts = Counter({t: c for t, c in doc_token_counts if t in topic_keywords})
        years[year].update(topic_token_counts)

    return jsonp(years)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--host',  metavar='host', dest='host', default='localhost',
                        help="hostname or ip address")
    parser.add_argument('--port', metavar='port', dest='port', type=int, default=8080,
                        help="port number")
    parser.add_argument('--debug', dest='debug', action='store_true',
                        help="enable debug mode")
    args = parser.parse_args()

    app.run(host=args.host, port=args.port, debug=args.debug)


