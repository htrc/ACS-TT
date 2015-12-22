#!/usr/bin/env python3
"""Tool for loading the processed Mallet topic modeling output into a MongoDB database"""

import argparse
import io
import os
import sys
import traceback

import pandas as pd
import numpy as np
from datetime import datetime
import pymongo
from pymongo import IndexModel, ASCENDING

remove_dataset = __import__('remove-dataset')  # needed due to the dash in the file name

__author__ = "Boris Capitanu"
__version__ = "1.0.0"


def load_distances(filename):
    """Read the file containing the calculated inter-topic distances

    :param filename: The file containing the calculated inter-topic distances
    :return: An upper-triangular matrix encoded as a vector
    """
    with open(filename, encoding='utf-8') as f:
        data = io.StringIO(f.read())

    with data:
        num_topics = len(data.readline().split(',')) - 1
        data.seek(0)  # rewind
        distances = pd.read_csv(filename, header=None, engine='c', skiprows=1, index_col=0)

    return distances.as_matrix()[np.triu_indices(num_topics, k=1)]


def load_csv(filename):
    """Generic method for loading a CSV file

    :param filename: The CSV file path
    :return: Array of dicts, one for each row or None if filename is None
    """
    if filename is None:
        return None

    return pd.read_csv(filename, engine='c', encoding='utf-8')


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


def parse_as_date(d, date_format):
    """Try to parse the given object as a date

    :param d: The object to parse
    :param date_format: The expected date format
    :return: The date if the parse succeeded, None otherwise
    """
    try:
        return datetime.strptime(str(d), date_format)
    except ValueError:
        return None


def run(dataset_name, mongo_uri, dbname, dist_file, docs_file, meta_file,
        state_file, tokens_file, topics_file, cby_file, cbty_file, date_format):
    print("Loading %s..." % dist_file, end='', flush=True)
    distances = load_distances(dist_file).tolist()
    print("done")

    print("Loading %s..." % docs_file, end='', flush=True)
    doc_topics = load_csv(docs_file)
    print("done")

    print("Loading %s..." % meta_file, end='', flush=True)
    doc_meta = load_csv(meta_file)
    doc_meta = pd.merge(doc_topics[['id', 'source']], doc_meta, on='source', how='left') \
        .rename(columns={'id': 'docid', 'id_x': 'docid', 'id_y': 'volid'}, copy=False)
    doc_meta.set_index(['docid'], inplace=True)
    doc_meta.sort_index(inplace=True)
    print("done")

    print("Loading %s..." % state_file, end='', flush=True)
    state = load_csv(state_file)
    state['tokenid'] = state['tokenid'].astype(int).astype(str)
    state.set_index(['topic', 'docid'], inplace=True)
    print("done")

    print("Loading %s..." % tokens_file, end='', flush=True)
    token_map = load_csv(tokens_file)
    token_map.set_index(['tokenid'], inplace=True)
    token_map.sort_index(inplace=True)
    print("done")

    print("Loading %s..." % topics_file, end='', flush=True)
    topics = load_csv(topics_file)
    topics.set_index(['id'], inplace=True)
    topics.sort_index(inplace=True)
    print("done")

    print("Loading %s..." % cby_file, end='', flush=True)
    corpus_token_counts_by_year = load_csv(cby_file).astype(object)
    corpus_token_counts_by_year['year'] = corpus_token_counts_by_year['year'].astype(int).astype(str)
    corpus_token_counts_by_year.set_index(['year'], inplace=True)
    print("done")

    print("Loading %s..." % cbty_file, end='', flush=True)
    topic_keyword_counts_by_year = load_csv(cbty_file)
    topic_keyword_counts_by_year['year'] = topic_keyword_counts_by_year['year'].astype(int).astype(str)
    topic_keyword_counts_by_year.set_index(['topic', 'year'], inplace=True)
    print("done")

    print("Creating dataset...")
    mongo = pymongo.MongoClient(mongo_uri)
    db = mongo[dbname]

    num_docs = len(doc_meta)
    num_tokens = len(token_map)
    num_topics = len(topics)

    num_kw_per_topic = topics.columns.str.startswith('key.').sum()

    # convert the publishDate into a real datetime object
    documents = doc_meta.to_dict(orient='records')
    for doc in documents:
        doc['publishDate'] = parse_as_date(doc['publishDate'], date_format)

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
        'tokens': token_map['token'].values.tolist(),
        'distances': distances,
        'centerDist': topics['dist'].values.tolist(),
        'documents': documents,
        'tokenCountsByYear': corpus_token_counts_by_year.to_dict()['count']
    }

    dataset_id = db.datasets.insert_one(dataset).inserted_id
    print("Dataset id: {}".format(dataset_id))

    try:
        for topic_id, topic_state in state.groupby(level=0):
            print("Adding topic {}...".format(topic_id), end='', flush=True)
            topic_docs = [{
                              'datasetId': dataset_id,
                              'topicId': topic_id.item(),
                              'docId': doc_id.item(),
                              'tokenCounts': doc_data.set_index(['tokenid']).to_dict()['count']
                          } for doc_id, doc_data in topic_state.astype(object).groupby(level=1)]

            topic_doc_allocation = doc_topics['topic.%s' % topic_id].values.tolist()
            topic = topics.loc[topic_id]
            topic_keywords = topic['key.0':'key.{}'.format(num_kw_per_topic - 1)].values.tolist()

            t = {
                'datasetId': dataset_id,
                'topicId': topic_id.item(),
                'alpha': topic['alpha'].item(),
                'trend': topic['trend'].item(),
                'mean': topic['mean'].item(),
                'keywords': topic_keywords,
                'docAllocation': topic_doc_allocation,
                'keywordCountsByYear': {
                    year: {
                        'keywords': counts['token'].values.tolist(),
                        'counts': counts['count'].values.tolist()
                    }
                    for year, counts in topic_keyword_counts_by_year.astype(object).loc[topic_id].groupby(level=0)
                }
            }

            db.topics.insert_one(t)
            db.state.insert_many(topic_docs)
            print("done, {:,} topic docs".format(len(topic_docs)))

        print("Creating indexes...", end='', flush=True)
        topic_composite_idx = IndexModel([
            ('datasetId', ASCENDING),
            ('topicId', ASCENDING)
        ], name='dataset_topic', unique=True)

        db.topics.create_indexes([topic_composite_idx])

        state_composite_idx = IndexModel([
            ('datasetId', ASCENDING),
            ('topicId', ASCENDING),
            ('docId', ASCENDING)
        ], name='dataset_state', unique=True)

        db.state.create_indexes([state_composite_idx])
        print("done")

        print("Finished.")
    except:
        traceback.print_exc(file=sys.stderr)
        # remove the partial dataset if an error occurred
        remove_dataset.remove_dataset(dataset_id, db)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Loads data produced by compute-galaxy.py into a MongoDB database",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--name', dest='dataset_name', required=True,
                        help="The name of the dataset")
    parser.add_argument('--mongo', dest='mongo_uri', default='mongodb://localhost:27017/',
                        help="The URI of the MongoDB instance to use")
    parser.add_argument('--dbname', dest='dbname', default='galaxyviewer',
                        help="The name of the database to use")
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
    parser.add_argument('--cby', dest='cby_filename', default='counts_by_year.csv',
                        help="The CSV file containing total token counts by year at the dataset level")
    parser.add_argument('--cbty', dest='cbty_filename', default='counts_by_topic_year.csv',
                        help="The CSV file containing token counts by topic by year")
    parser.add_argument('--meta', dest='meta_filename', default='docmeta.csv',
                        help="The metadata file containing info about each document")
    parser.add_argument('--date-format', dest='date_format', metavar='FORMAT', default='%Y-%m-%dT%H:%M:%SZ',
                        help="Date format to interpret metadata publishDate (used with datetime.datetime.strptime)")

    args = parser.parse_args()
    dataset_name = args.dataset_name
    mongo_uri = args.mongo_uri
    dbname = args.dbname
    dist_file = args.distance_filename
    docs_file = args.documents_filename
    state_file = args.state_filename
    tokens_file = args.tokens_filename
    topics_file = args.topics_filename
    cby_file = args.cby_filename
    cbty_file = args.cbty_filename
    meta_file = args.meta_filename
    date_format = args.date_format

    if meta_file is not None and not os.path.exists(meta_file):
        sys.exit("File not found: " + meta_file)

    for f in [dist_file, docs_file, state_file, tokens_file, topics_file, cby_file, cbty_file]:
        if not os.path.exists(f):
            sys.exit("File not found: " + f)

    run(dataset_name, mongo_uri, dbname, dist_file, docs_file, meta_file,
        state_file, tokens_file, topics_file, cby_file, cbty_file, date_format)
