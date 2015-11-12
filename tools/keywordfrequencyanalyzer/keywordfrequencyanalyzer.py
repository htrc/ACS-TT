#!/usr/bin/env python

"""Keyword Frequency Analyzer

This script calculates the relative frequencies of a list of keywords.
The results can be used to classify documents, given a careful choice of the keywords.
The script outputs the frequency of each word, and the sum of relative frequencies of
all keywords per text, to a CSV file.
"""

from __future__ import print_function
import argparse
import csv
import glob
import json
import os
import sys
import time
from datetime import timedelta
from functools import partial
from io import open, StringIO
from multiprocessing import Pool
from urllib2 import Request, urlopen, URLError, HTTPError
from zipfile import ZipFile
import regex
from pairtree import pairtree_path

__author__ = "Kevin Schenk, Boris Capitanu"
__version__ = "1.2.0"


SOLR_QUERY_TPL = "http://chinkapin.pti.indiana.edu:9994/solr/meta/select?q=id:{}&fl=title,author,publishDate" \
                 "&wt=json&omitHeader=true"
PAIRTREE_REGEX = regex.compile(ur"(?P<libid>[^/]+)/pairtree_root/(?P<ppath>.+)/(?P<cleanid>[^/]+)\.[^.]+$")
EOL_HYPHEN_REGEX = regex.compile(ur"(?m)(\S*\p{L})-\s*\n(\p{L}\S*)\s*")
PUNCT_REGEX = regex.compile(ur"[^\P{P}-']+")
CONTRACTION_REGEX = regex.compile(ur"'s\b")


def clean_and_normalize(text):
    """Clean the specified text by combining end-of-line hyphenated words, removing punctuation, etc.
    :param text: The text
    :return: The cleaned text
    """
    text = EOL_HYPHEN_REGEX.sub(r"\1\2\n", text)  # join end-of-line hyphenated words
    text = PUNCT_REGEX.sub(" ", text)  # remove all punctuation except hyphens and apostrophes
    text = CONTRACTION_REGEX.sub("", text)  # remove the 's contraction from words (as required by project specs)
    text = text.lower()
    return text


def drop_untracked_tokens(words, tracked_tokens):
    """Reduce the problem space by dropping all words that are not part of the keywords list
    :param words: The list words making up the text to be processed
    :param tracked_tokens: The unique set of words (tokens) that are part of the keyword list
    :return: The reduced set of words with all non-keyword words removed (and replaced by a separator)
    """
    tracked_wordseq = []
    marker_added = False
    for w in words:
        if w not in tracked_tokens:
            if not marker_added:
                tracked_wordseq.append('|')
                marker_added = True
        else:
            tracked_wordseq.append(w)
            marker_added = False

    return tracked_wordseq


def find_relative_frequencies(text, keywords_regexps, tokens=None):
    """Calculate the relative frequencies of a set of keywords in a text document
    :param text: The text document
    :param keywords_regexps: The keyword -> regexp map for finding occurrences of the keyword in the text
    :param tokens: The unique set of tokens that are part of the keywords
    :return: The word count and relative frequency values
    """
    text_freqs = {}
    rel_freqs = {}

    text = clean_and_normalize(text)
    words = text.split()
    word_count = len(words)
    rel_freqs["WordCount"] = word_count

    if tokens is not None:
        words = drop_untracked_tokens(words, tracked_tokens=tokens)
        text = ' '.join(words)

    for keyword in keywords_regexps.keys():
        text_freqs[keyword] = len(keywords_regexps[keyword].findall(text))

    rel_freq_sum = 0
    for key, value in text_freqs.items():
        rel_freq_sum += float(value) / float(word_count)

    rel_freqs["RelFreqSum"] = rel_freq_sum
    rel_freqs["Frequencies"] = text_freqs

    return rel_freqs


def log_freqs(result, file_path, output_csv, keywords):
    """Saves the result to the output CSV
    :param result: The word count and relative frequency values
    :param file_path: The file path of the file being processed
    :param output_csv: The output CSV file object
    :param keywords: The keywords
    :return:
    """
    # TODO: Title, Author, etc.
    text_freqs = result["Frequencies"]

    # add default values for missing attributes
    for attr in ["VolID", "Title", "Author", "Year"]:
        result.setdefault(attr, "")

    output_csv.writerow(
        [file_path.encode('utf-8'),
         result["VolID"].encode('utf-8'),
         result["Title"].encode('utf-8'),
         result["Author"].encode('utf-8'),
         result["Year"].encode('utf-8'),
         result["WordCount"],
         result["RelFreqSum"]
         ] + [text_freqs[keyword] for keyword in keywords])


def get_htrc_id(zip_path):
    """Parses a pairtree path to extract the HT volume ID
    :param zip_path: The path to the HT pairtree ZIP file
    :return: The HT volume id
    """
    pt_parts = PAIRTREE_REGEX.search(zip_path)
    libid = pt_parts.group("libid")
    cleanid = pt_parts.group("cleanid")
    htrc_id = pairtree_path.id_decode("{}.{}".format(libid, cleanid))

    return htrc_id


def get_meta(htrc_id):
    """Retrieves volume metadata for a volume referenced by `htrc_id`
    :param htrc_id: The HT id
    :return: The metadata object for the volume (or empty if error occurred)
    """
    meta = {}
    query = SOLR_QUERY_TPL.format(htrc_id.replace(":", "\\:"))
    req = Request(query)
    try:
        url = urlopen(req)
    except HTTPError as e:
        print("{}: get_meta({}): The server couldn't fulfill the request.".format(htrc_id, e.code))
    except URLError as e:
        print("{}: Failed to contact SOLR. Reason: {}".format(htrc_id, e.reason))
    else:
        respdata = url.read()
        try:
            response = respdata.decode("utf-8")
        except UnicodeDecodeError:
            try:
                response = respdata.decode("cp1252")
            except:
                print("{}: Cannot decode response from SOLR".format(htrc_id))
                return meta
        response = json.loads(response)["response"]
        url.close()
        num_found = response["numFound"]
        if num_found == 0:
            print("{}: No metadata found in SOLR.".format(htrc_id))
        else:
            if num_found > 1:
                print("{}: {} metadata records were found - using the first result.".format(htrc_id, num_found))
            doc = response["docs"][0]
            if "title" in doc:
                meta["Title"] = "; ".join(doc["title"])
            if "author" in doc:
                meta["Author"] = "; ".join(doc["author"])
            if "publishDate" in doc:
                meta["Year"] = "; ".join(doc["publishDate"])

    return meta


def process_zip_volume(zip_path, keywords_regexps, tokens=None):
    """Processes a HT pairtree ZIP volume to calculate the relative frequency values of the given keywords
    :param zip_path: The path to the HT pairtree volume ZIP file
    :param keywords_regexps: The keyword -> regexp mapping
    :param tokens: The unique set of tokens that are part of the keywords
    :return: The relative frequencies
    """
    htrc_id = get_htrc_id(zip_path)

    print("Finding frequencies for: {}".format(htrc_id))

    meta = get_meta(htrc_id)
    text = StringIO()

    with ZipFile(zip_path, 'r') as zipfile:
        page_files = [zip_entry.filename for zip_entry in zipfile.infolist() if
                      zip_entry.filename.lower().endswith(".txt")]
        for filename in sorted(page_files):
            text.write(u' ')
            text.write(zipfile.read(filename).decode('utf-8'))

    text = text.getvalue()

    rel_freqs = find_relative_frequencies(text, keywords_regexps, tokens)
    rel_freqs.update(meta)
    rel_freqs["VolID"] = htrc_id

    return rel_freqs


def process_txt_volume(file_path, keywords_regexps, tokens=None):
    """Processes a text file to calculate the relative frequency values of the given keywords
    :param file_path: The text file path
    :param keywords_regexps: The keyword -> regexp mapping
    :param tokens: The unique set of tokens that are part of the keywords
    :return: The relative frequencies
    """
    root, filename = os.path.split(file_path)
    print("Finding frequencies for " + filename)

    with open(file_path, encoding='utf-8') as text_file:
        text = text_file.read()

    rel_freqs = find_relative_frequencies(text, keywords_regexps, tokens)

    # rel_freqs["Title"] =
    # rel_freqs["Author"] =
    # rel_freqs["Year"] =
    rel_freqs["VolID"] = filename

    return rel_freqs


def read_keyword_file(keyword_filename):
    """Read the keyword file
    :param keyword_filename: The path to the keywords file
    :return: The keywords
    """
    keywords = set()

    with open(keyword_filename, encoding='utf-8') as keyword_file:
        for line in keyword_file.readlines():
            words = line.lower().split()

            if not words:  # skip empty lines
                continue

            keywords.add(tuple(words))

    return keywords


def build_keyword_regexps(keywords):
    """Builds a regular expression for each keyword to aid in looking up that keyword in the text
    :param keywords: The keywords
    :return: The keyword -> regexp mapping for all the keywords
    """
    keywords_regexps = {}

    for keyword in keywords:
        keywords_regexps[keyword] = regex.compile('\\b' + regex.escape(' '.join(keyword), special_only=True) + '\\b')

    return keywords_regexps


def run(keyword_filename, glob_pattern, pt_path, output_filename):
    start_time = time.time()

    keywords = read_keyword_file(keyword_filename)
    print("Keywords read: {}".format(len(keywords)))

    tokens = set(token for keyword in keywords for token in keyword)
    keywords_regexps = build_keyword_regexps(keywords)

    print("Reading volume files.")
    num_files = 0

    pool = Pool()
    with open(output_filename, 'wb') as csv_file:
        try:
            output_csv = csv.writer(csv_file)
            output_csv.writerow(
                ["Filename", "VolID", "Title", "Author", "Year", "WordCount", "RelFreqSum"] +
                [" ".join(k).encode('utf-8') for k in keywords])

            if glob_pattern is not None:
                for volume_path in glob.iglob(glob_pattern):
                    num_files += 1
                    pool.apply_async(process_txt_volume, (volume_path, keywords_regexps, tokens,),
                                     callback=partial(log_freqs,
                                                      file_path=volume_path,
                                                      output_csv=output_csv,
                                                      keywords=keywords))
            elif pt_path is not None:
                for root, dirs, files in os.walk(pt_path):
                    for zip_file in [file_path for file_path in files if file_path.lower().endswith(".zip")]:
                        num_files += 1
                        volume_path = os.path.join(root, zip_file)
                        pool.apply_async(process_zip_volume, (volume_path, keywords_regexps, tokens,),
                                         callback=partial(log_freqs,
                                                          file_path=volume_path,
                                                          output_csv=output_csv,
                                                          keywords=keywords))
        finally:
            pool.close()
            pool.join()

    print("Files processed: {}".format(num_files))

    elapsed = int(time.time() - start_time)
    print("Time elapsed: {}".format(timedelta(seconds=elapsed)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Calculate the frequency of keywords in text files. '
                    'Creates an output file ranking by relative frequency.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--keywords', dest='keyword_filename', required=True,
                        help='A text file containing the line-break-separated keywords to use')
    parser.add_argument('--output', dest='output_filename', required=True,
                        help="The output CSV file")

    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--glob', dest='glob_pattern',
                        help="A glob pattern specifying the files to process")
    action.add_argument('--pairtree', dest='pairtree_path',
                        help="The root folder of the HT pairtree hierarchy to process")

    args = parser.parse_args()

    keyword_filename = args.keyword_filename
    output_filename = args.output_filename
    glob_pattern = args.glob_pattern
    pt_path = args.pairtree_path

    if not os.path.exists(keyword_filename):
        sys.exit("Keywords file not found: {}".format(keyword_filename))

    if pt_path is not None and not os.path.exists(pt_path):
        sys.exit("Pairtree path not found: {}".format(pt_path))

    run(keyword_filename, glob_pattern, pt_path, output_filename)
