#!/usr/bin/env python3
"""Tool for removing a dataset previously loaded into a MongoDB database"""

import argparse
import pymongo

__author__ = "Boris Capitanu"
__version__ = "1.0.0"


def find_dataset_id(dataset_name, db):
    """Attempts to find the dataset ID for a given dataset name

    :param dataset_name: The dataset name
    :param db: The db instance
    :return: The dataset ID
    :raises ValueError: if the given dataset_name doesn't exist
    """
    dataset = db.datasets.find_one({'name': dataset_name}, {'_id': 1})
    if dataset is None:
        raise ValueError("Dataset '%s' not found" % dataset_name)

    return dataset['_id']


def remove_dataset(dataset_id, db):
    """Remove a dataset from the database

    :param dataset_id: The dataset id
    :param db: The db instance
    :return: (deleted_count_datasets, deleted_count_topics, deleted_count_state) pair
    """

    dd = db.datasets.delete_one({'_id': dataset_id}).deleted_count
    dt = db.topics.delete_many({'datasetId': dataset_id}).deleted_count
    ds = db.state.delete_many({'datasetId': dataset_id}).deleted_count

    return dd, ds, dt


def run(dataset_name, dbname, mongo_uri):
    print("Using database: {}{}".format(mongo_uri, dbname))
    mongo = pymongo.MongoClient(mongo_uri)
    db = mongo[dbname]

    try:
        dataset_id = find_dataset_id(dataset_name, db)
    except ValueError as e:
        print(str(e))
        return

    print("Found dataset '{}' with id {}".format(dataset_name, dataset_id))
    dd, ds, dt = remove_dataset(dataset_id, db)
    print("Removed: datasets({}) topics({}) state({})".format(dd, dt, ds))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Removes a dataset previously loaded into a MongoDB database",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--name', dest='dataset_name', required=True,
                        help="The name of the dataset")
    parser.add_argument('--mongo', dest='mongo_uri', default='mongodb://localhost:27017/',
                        help="The URI of the MongoDB instance to use")
    parser.add_argument('--dbname', dest='dbname', default='galaxyviewer',
                        help="The name of the database to use")

    args = parser.parse_args()
    dataset_name = args.dataset_name
    dbname = args.dbname
    mongo_uri = args.mongo_uri

    run(dataset_name, dbname, mongo_uri)
