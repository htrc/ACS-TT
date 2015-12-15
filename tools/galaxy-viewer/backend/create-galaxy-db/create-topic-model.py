#!/usr/bin/env python3
"""Runs the Mallet topic modeling algorithm on a supplied corpus.

Tool used to run the topic modeling algorithm from the Mallet toolkit
on a set of text documents referenced via the command line arguments.
Optionally, additional facilities for stopword removal and token pruning
are provided via specific command line arguments.

Note: This is a very slow process due to the extra pre-processing done
      to remove stopwords and perform pruning, which causes the generation
      of an intermediary dataset containing the result, which is then further
      converted into a Mallet-specific input format before finally the topic
      modeling algorithm is run.

      If the additional stopword removal and token pruning is not needed,
      then faster processing (with identical result) will be obtained by
      directly running the Mallet tool manually on the data, via the
      Mallet-supplied 'mallet' script, as per Mallet's documentation.
"""

import logging
import glob
import argparse
import os
import sys
from gensim import corpora, models, utils

__author__ = "Ryan Chartier, Boris Capitanu"
__version__ = "1.0.0"


def read_stopwords(stopwords_file):
    """Returns the set of stop words read from the specified file
    :param stopwords_file: The path to the file containing the stop words
    :return: The set of stop words
    """
    with open(stopwords_file) as f:
        stopwords = set(f.read().split())

    return stopwords


def tokenize(doc, *, stopwords=None):
    """Tokenizes a document (optionally removing stopwords)
    :param doc: A file-like object supporting .read()
    :param stopwords: The set of stopwords to remove
    :return: The list of tokens of the document
    """
    text = doc.read()

    tokens = utils.simple_preprocess(text, deacc=True)
    if stopwords is not None:
        tokens = [t for t in tokens if t not in stopwords]

    return tokens


class Corpus(object):
    def __init__(self, glob_pattern, *, stopwords=None, prune_below=None, prune_above=None):
        """Initializes a Corpus object
        :param glob_pattern: The glob representing the set of files comprising the corpus
        :param stopwords: If provided, these stop words will be removed during the tokenization of the text
        :param prune_below: Filter out tokens that appear in less than `prune_below` documents (absolute number)
        :param prune_above: Filter out tokens that appear in more than `prune_above` documents (fraction of total
                            corpus size, *not* absolute number; 0 <= prune_below <= 1.0)
        :return: A corpus instance
        """
        self._glob_pattern = glob_pattern
        self._stopwords = stopwords
        self._prune_below = prune_below
        self._prune_above = prune_above
        self._dictionary = None

    @property
    def tokenized_docs(self):
        """Generator for sequences of tokens for each document
        :return: A generator over sequences of tokens for each document in the corpus
        """
        for doc in glob.iglob(self._glob_pattern, recursive=True):
            with open(doc) as d:
                tokens = tokenize(d, stopwords=self._stopwords)
            yield tokens

    @property
    def dictionary(self):
        """Dictionary that encapsulates the mapping between normalized words and their integer ids
        :return: A dictionary whose main function is `doc2bow`, which converts a collection of words to its
                 bag-of-words representation: a list of (word_id, word_frequency) 2-tuples.
        """
        if self._dictionary is None:
            self._dictionary = corpora.Dictionary(self.tokenized_docs)
            if self._prune_below or self._prune_above is not None:
                self._dictionary.filter_extremes(no_below=self._prune_below or 0,
                                                 no_above=self._prune_above or 1.0)
        return self._dictionary

    def __iter__(self):
        """Iterator over the bag-of-words representation of each document in the corpus
        :return: An iterator over the bag-of-words representation of each document in the corpus
        """
        for tokens in self.tokenized_docs:
            yield self.dictionary.doc2bow(tokens)


def run(glob_pattern, stopword_filename, prune_below, prune_above,
        mallet_bin, num_topics, num_iter, num_workers, output_dir):

    stopwords = read_stopwords(stopword_filename) if stopword_filename is not None else None

    # ensure output_dir ends with a / (for unix systems) or \ (for windows systems)
    # this is important for the LdaMallet's prefix argument
    if not output_dir.endswith(os.path.sep):
        output_dir += os.path.sep

    # ensure output_dir exists
    os.makedirs(output_dir, exist_ok=True)

    corpus = Corpus(glob_pattern, stopwords=stopwords, prune_below=prune_below, prune_above=prune_above)
    model = models.wrappers.LdaMallet(mallet_bin, corpus, num_topics=num_topics, id2word=corpus.dictionary,
                                      iterations=num_iter, workers=num_workers, prefix=output_dir)

    # dump the arguments in args.txt in the output_dir for future reference
    with open(os.path.join(output_dir, 'args.txt'), 'w') as f:
        f.write(' '.join(sys.argv))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Runs Mallet to create the topic model for the provided corpus",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--mallet-bin', dest='mallet_bin', metavar='PATH', default='mallet',
                        help="The path of the Mallet startup script")
    parser.add_argument('--remove-stopwords', dest='stopword_filename', metavar='FILE',
                        help="The path to the stopwords file to use in addition to the default Mallet stopword list "
                             "(one word per line); if not provided, only the default Mallet stopword list is used")
    parser.add_argument('--prune-below', dest='prune_below', metavar='MIN', type=int,
                        help="Filter out tokens that appear in less than MIN documents (absolute number)")
    parser.add_argument('--prune-above', dest='prune_above', metavar='MAX', type=float,
                        help="Filter out tokens that appear in more than MAX percent of documents (0 < MAX < 1)")
    parser.add_argument('--num-topics', dest='num_topics', metavar='N', type=int, default=100,
                        help="The number of topics to generate")
    parser.add_argument('--num-iter', dest='num_iter', metavar='N', type=int, default=1000,
                        help="The number of sampling iterations")
    parser.add_argument('--num-workers', dest='num_workers', metavar='N', type=int, default=4,
                        help="The number of parallel workers to use")
    parser.add_argument('--output', dest='output_dir', metavar='DIR', required=True,
                        help="The output folder where the results should be written to")
    parser.add_argument('glob_pattern', metavar='glob',
                        help="The glob pattern specifying the text files that are part of the corpus")

    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

    args = parser.parse_args()
    mallet_bin = args.mallet_bin
    stopword_filename = args.stopword_filename
    prune_below = args.prune_below
    prune_above = args.prune_above
    output_dir = args.output_dir
    num_topics = args.num_topics
    num_iter = args.num_iter
    num_workers = args.num_workers
    glob_pattern = args.glob_pattern

    run(glob_pattern, stopword_filename, prune_below, prune_above,
        mallet_bin, num_topics, num_iter, num_workers, output_dir)
