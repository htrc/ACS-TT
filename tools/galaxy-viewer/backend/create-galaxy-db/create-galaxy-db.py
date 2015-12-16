#!/usr/bin/env python3
"""Tool for loading the processed Mallet topic modeling output into a MongoDB database"""

import argparse
import collections
import csv
import os
import sys

import dateutil.parser
import datetime
import pymongo
from pymongo import IndexModel, ASCENDING
from numbers import Number

__author__ = "Boris Capitanu"
__version__ = "1.0.0"


def try_parse_number(x):
    """Helper method for identifying and returning numbers, where possible.

    :param x: The potential number
    :return: The number representation of the argument, or the original argument if not a number
    """
    try:
        return int(x)
    except ValueError:
        try:
            return float(x)
        except ValueError:
            return x


def load_distances(filename):
    """Read the file containing the calculated inter-topic distances

    :param filename: The file containing the calculated inter-topic distances
    :return: An upper-triangular matrix encoded as a vector
    """
    data = []
    with open(filename, encoding='utf-8') as f:
        reader = csv.reader(f, quoting=csv.QUOTE_NONE)
        next(reader)  # skip header
        skip = 0
        for line in reader:
            data.append([try_parse_number(col) for col in line[2 + skip:]])
            skip += 1

    # only keep the upper triangular matrix (less diagonal) to prevent redundancy
    return [item for sublist in data for item in sublist]


def load_csv(filename):
    """Generic method for loading a CSV file

    :param filename: The CSV file path
    :return: Array of dicts, one for each row or None if filename is None
    """
    if filename is None:
        return None

    data = []
    with open(filename, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({k: try_parse_number(v) for k, v in row.items()})

    return data


def get_distance(num_topics, distances, topic_x, topic_y):
    """Indexing method into the upper-triangular matrix representing inter-topic distances

    :param num_topics: The number of topics
    :param distances: The upper-triangular matrix representing inter-topic distances
    :param topic_x: The id of the first topic
    :param topic_y: The id of the second topic
    :return: The distance between topic_x and topic_y
    """
    if topic_x == topic_y:
        return 0

    x = min(topic_x, topic_y)
    y = max(topic_x, topic_y)
    n = num_topics

    i = int((2 * x * n - x ** 2 + 2 * y - 3 * x - 2) / 2)

    return distances[i]


def parse_state(data):
    """Reads the topic modeling state data

    :param data: An iterable over the state data rows
    :return: A dictionary mapping (topic_id, doc_id) to (token_id, count)
    """
    state = collections.defaultdict(lambda: collections.defaultdict(list))

    for row in data:
        doc_id, token_id, topic_id, count = row['docid'], row['tokenid'], row['topic'], row['count']
        state[topic_id][doc_id].append((token_id, count))

    return state


def get_docs_meta(doc_meta, doc_topics):
    """Parses metadata for each document into an appropriate format for use with the Galaxy Viewer

    :param doc_meta: The document metadata
    :param doc_topics: The topic allocation for each document
    :return: An array of document metadata, with one entry per document
    :raises ValueError: if 'doc_meta' does not contain metadata for all documents referenced in 'doc_topics'
    """
    if doc_meta is None:
        documents = [{
                         'title': doc['title'],
                         'source': doc['source'],
                         'publishDate': dateutil.parser.parse(str(doc['publishDate']))
                     } for doc in doc_topics]
    else:
        docs = {meta['source']: meta for meta in doc_meta}
        documents = []
        for doc in doc_topics:
            source = doc['source']
            meta = docs.get(source)
            if meta is None:
                raise ValueError("Missing metadata for: %s" % source)
            if 'id' in meta:
                meta['volid'] = meta.pop('id')  # rename the field (GV expects 'volid')
            doc_date = meta['publishDate']
            if isinstance(doc_date, Number):
                if doc_date > 0:
                    doc_date = datetime.datetime(doc_date, 1, 1)
                else:
                    doc_date = None
            else:
                doc_date = dateutil.parser.parse(str(doc_date))
            meta['publishDate'] = doc_date
            documents.append(meta)

    return documents


def run(dataset_name, dist_file, docs_file, meta_file, state_file, tokens_file, topics_file, dbname, mongo_uri):
    distances = load_distances(dist_file)
    doc_topics = load_csv(docs_file)
    doc_meta = load_csv(meta_file)
    state = parse_state(load_csv(state_file))
    tokens = load_csv(tokens_file)
    topics = load_csv(topics_file)

    documents = get_docs_meta(doc_meta, doc_topics)

    mongo = pymongo.MongoClient(mongo_uri)
    db = mongo[dbname]

    num_docs = len(documents)
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
        'documents': documents
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
            'docAllocation': [topic_alloc['topic.{}'.format(topic_id)] for topic_alloc in doc_topics]
        }
        db.topics.insert_one(t)
        db.state.insert_many([{
                                  'datasetId': dataset_id,
                                  'topicId': topic_id,
                                  'docId': doc_id,
                                  'tokens': [token_id for token_id, _ in token_counts],
                                  'counts': [count for _, count in token_counts]
                              } for doc_id, token_counts in state[topic_id].items()])

    topic_composite_idx = IndexModel([
        ('datasetId', ASCENDING),
        ('topicId', ASCENDING)
    ], name='dataset_topic', unique=True)

    db.topics.create_indexes([topic_composite_idx])

    state_composite_idx = IndexModel([
        ('datasetId', ASCENDING),
        ('topicId', ASCENDING),
        ('docId', ASCENDING)
    ], name='dataset_topic', unique=True)

    db.state.create_indexes([state_composite_idx])

    print("All done.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Loads data produced by compute-galaxy.py into a MongoDB database",
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
    parser.add_argument('--meta', dest='meta_filename', default='docmeta.csv',
                        help="The metadata file containing info about each document")

    args = parser.parse_args()
    dist_file = args.distance_filename
    docs_file = args.documents_filename
    state_file = args.state_filename
    tokens_file = args.tokens_filename
    topics_file = args.topics_filename
    dataset_name = args.dataset_name
    dbname = args.dbname
    mongo_uri = args.mongo_uri
    meta_file = args.meta_filename

    if meta_file is not None and not os.path.exists(meta_file):
        sys.exit("File not found: " + meta_file)

    for f in [dist_file, docs_file, state_file, tokens_file, topics_file]:
        if not os.path.exists(f):
            sys.exit("File not found: " + f)

    run(dataset_name, dist_file, docs_file, meta_file, state_file, tokens_file, topics_file, dbname, mongo_uri)
