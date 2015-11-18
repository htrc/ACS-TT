import argparse
import collections
import csv
import os
import sys

import dateutil.parser
import pymongo
from pymongo import IndexModel, ASCENDING


def parse_number(x):
    try:
        return int(x)
    except ValueError:
        try:
            return float(x)
        except ValueError:
            return x


def load_distances(filename):
    data = []
    with open(filename, encoding='utf-8') as f:
        reader = csv.reader(f, quoting=csv.QUOTE_NONE)
        next(reader)  # skip header
        skip = 0
        for line in reader:
            data.append([parse_number(col) for col in line[2 + skip:]])
            skip += 1

    # only keep the upper triangular matrix (less diagonal) to prevent redundancy
    return [item for sublist in data for item in sublist]


def load_csv(filename):
    data = []
    with open(filename, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({k: parse_number(v) for k, v in row.items()})

    return data


def get_distance(num_topics, distances, topic_x, topic_y):
    if topic_x == topic_y:
        return 0

    x = min(topic_x, topic_y)
    y = max(topic_x, topic_y)
    n = num_topics

    i = int((2 * x * n - x ** 2 + 2 * y - 3 * x - 2) / 2)

    return distances[i]


def parse_state(data):
    state = collections.defaultdict(lambda: collections.defaultdict(list))

    for row in data:
        doc_id, token_id, topic_id, count = row['doc'], row['token'], row['topic'], row['count']
        state[topic_id][doc_id].append((token_id, count))

    return state


def run(dataset_name, dist_file, docs_file, state_file, tokens_file, topics_file, dbname, mongo_uri):
    distances = load_distances(dist_file)
    doc_topics = load_csv(docs_file)
    state = parse_state(load_csv(state_file))
    tokens = load_csv(tokens_file)
    topics = load_csv(topics_file)

    mongo = pymongo.MongoClient(mongo_uri)
    db = mongo[dbname]

    num_docs = len(doc_topics)
    num_tokens = len(tokens)
    num_topics = len(topics)

    num_kw_per_topic = len([key for key in topics[0].keys() if key.startswith('key.')])

    print("Dataset: {}".format(dataset_name))
    print("Number of documents: {:,}".format(num_docs))
    print("Vocabulary size: {:,}".format(num_tokens))
    print("Number of topics: {:,}".format(num_topics))
    print("Number of keywords per topic: {:,}".format(num_kw_per_topic))

    dataset = {
        'name': dataset_name,
        'numDocs': num_docs,
        'numTopics': num_topics,
        'numTokens': num_tokens,
        'tokens': tokens,
        'distances': distances,
        'centerDist': list(map(lambda topic: topic['dist'], topics)),
        'documents': [{
            'name': doc['name'],
            'source': doc['source'],
            'date': dateutil.parser.parse(doc['date'])
        } for doc in doc_topics]
    }

    dataset_id = db.datasets.insert_one(dataset).inserted_id
    print("Dataset id: {}".format(dataset_id))

    for topic in topics:
        topic_id = topic['id']
        t = {
            'datasetId': dataset_id,
            'topicId': topic_id,
            'alpha': topic['alpha'],
            'trend': topic['trend'],
            'mean': topic['mean'],
            'keywords': [topic[key] for key in map(lambda x: 'key.{}'.format(x), range(num_kw_per_topic))],
            'docAllocation': [topic_alloc['topic.{}'.format(topic_id)] for topic_alloc in doc_topics],
            'documents': [{
                'id': doc_id,
                'tokens': [token_id for token_id, _ in token_counts],
                'counts': [count for _, count in token_counts]
            } for doc_id, token_counts in state[topic_id].items()]
        }

        db.topics.insert_one(t)

    composite_idx = IndexModel([
        ('datasetId', ASCENDING),
        ('topicId', ASCENDING)
    ], name='dataset_topic', unique=True)

    db.topics.create_indexes([composite_idx])

    print("All done.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Converts data created by the GalaxyViewer backend R scripts to "
                    "Javascript files for ingestion into MongoDB",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--dist', dest='distance_filename', default='distance.csv',
                        help="The topic distance CSV file")
    parser.add_argument('--docs', dest='documents_filename', default='documents.csv',
                        help="The CSV file containing topic allocations for each document")
    parser.add_argument('--state', dest='state_filename', default='state.csv',
                        help="The Mallet state CSV file")
    parser.add_argument('--tokens', dest='tokens_filename', default='tokens.csv',
                        help="The CSV file containing id <-> token mapping")
    parser.add_argument('--topics', dest='topics_filename', default='topics.csv',
                        help="The topics CSV file")
    parser.add_argument('--name', dest='dataset_name', required=True,
                        help="The name of the dataset")
    parser.add_argument('--mongo', dest='mongo_uri', default='mongodb://localhost:27017/',
                        help="The URI of the MongoDB instance to use")
    parser.add_argument('--dbname', dest='dbname', default='galaxyviewer',
                        help="The name of the database to use")

    args = parser.parse_args()
    dist_file = args.distance_filename
    docs_file = args.documents_filename
    state_file = args.state_filename
    tokens_file = args.tokens_filename
    topics_file = args.topics_filename
    dataset_name = args.dataset_name
    dbname = args.dbname
    mongo_uri = args.mongo_uri

    for f in [dist_file, docs_file, state_file, tokens_file, topics_file]:
        if not os.path.exists(f):
            sys.exit("File not found: " + f)

    run(dataset_name, dist_file, docs_file, state_file, tokens_file, topics_file, dbname, mongo_uri)
