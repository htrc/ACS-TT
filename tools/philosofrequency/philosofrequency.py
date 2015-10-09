from __future__ import print_function
from operator import itemgetter
from multiprocessing import Pool
from functools import partial
from contextlib import closing
from zipfile import ZipFile
from urllib import quote
from urllib2 import Request, urlopen, URLError, HTTPError
from pairtree import pairtree_path
from io import open, StringIO
from itertools import islice
from collections import Counter
from datetime import timedelta

import sys, os, argparse, time, csv, regex, json

SOLR_QUERY_TPL = "http://chinkapin.pti.indiana.edu:9994/solr/meta/select?q=id:{}&fl=title,author,publishDate&wt=json&omitHeader=true"
PAIRTREE_REGEX = regex.compile(r"(?P<libid>[^/]+)/pairtree_root/(?P<ppath>.+)/(?P<cleanid>[^/]+)\.[^.]+$")
EOL_HYPHEN_REGEX = regex.compile(ur"(?m)(\S*\p{L})-\s*\n(\p{L}\S*)\s*")
PUNCT_REGEX = regex.compile(ur"[^\P{P}-']+")
CONTRACTION_REGEX = regex.compile(ur"'s\b")


def window(seq, n=2):
    "Returns a sliding window (of width n) over data from the iterable"
    "   s -> (s0,s1,...s[n-1]), (s1,s2,...,sn), ...                   "
    it = iter(seq)
    result = tuple(islice(it, n))
    if len(result) == n:
        yield result    
    for elem in it:
        result = result[1:] + (elem,)
        yield result

def clean_and_normalize(text):
    text = EOL_HYPHEN_REGEX.sub(r"\1\2\n", text)  # join end-of-line hyphenated words
    text = PUNCT_REGEX.sub(" ", text)  # remove all punctuation except hyphens and apostrophes
    text = CONTRACTION_REGEX.sub("", text)  # remove the 's contraction from words
    text = text.lower()
    return text

def findrelativefrequencies(text, keywords):
    textfreqs = Counter()
    relfreqs = {}

    words = clean_and_normalize(text).split()
    wordcount = len(words)
    relfreqs["WordCount"] = wordcount

    if wordcount > 1:
        counter = Counter()
        for w1, w2 in window(words):
            if w1 in tokens:
                counter[(w1,)] += 1
                counter[(w1, w2)] += 1

        if w2 in tokens:
            counter[(w2,)] += 1

        for k in keywords:
            if len(k) == 1:
                textfreqs[k] = counter[k]
            else:
                textfreqs[k] = min(counter[part] for part in window(k))
    else:
        for w in words:
            if (w,) in keywords:
                textfreqs[(w,)] = 1

    relfreqtotal = 0
    for key, value in textfreqs.items():
        relfreqtotal += float(value) / float(wordcount)

    relfreqs["RelFreqSum"] = relfreqtotal
    relfreqs["Frequencies"] = textfreqs

    return relfreqs

def log_freqs(result, file, ):
    # TODO: Title, Author, etc.
    textfreqs = result["Frequencies"]

    # add default values for missing attributes
    for attr in ["VolID", "Title", "Author", "Year"]:
        result.setdefault(attr, "")

    outputcsv.writerow(
        [file.encode('utf-8'),
         result["VolID"].encode('utf-8'),
         result["Title"].encode('utf-8'),
         result["Author"].encode('utf-8'),
         result["Year"].encode('utf-8'),
         result["WordCount"],
         result["RelFreqSum"]
        ] + [textfreqs[keyword] for keyword in keywords])

def get_htrc_id(zippath):
    pt_parts = PAIRTREE_REGEX.search(zippath)
    libid = pt_parts.group("libid")
    cleanid = pt_parts.group("cleanid")
    htrc_id = pairtree_path.id_decode("{}.{}".format(libid, cleanid))

    return htrc_id

def get_meta(htrc_id):
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
            response = json.loads(respdata.decode("utf-8"))["response"]
        except UnicodeDecodeError as e:
            print("{}: {}".format(htrc_id, e))
            return meta
        url.close()
        numFound = response["numFound"]
        if numFound == 0:
            print("{}: No metadata found in SOLR.".format(htrc_id))
        else:
            if numFound > 1:
                print("{}: {} metadata records were found - using the first result.".format(htrc_id, numFound))
            doc = response["docs"][0]
            if "title" in doc:
                meta["Title"] = "; ".join(doc["title"])
            if "author" in doc:
                meta["Author"] = "; ".join(doc["author"])
            if "publishDate" in doc:
                meta["Year"] = "; ".join(doc["publishDate"])

    return meta

def processzipvolume(zippath):
    root, file = os.path.split(zippath)

    htrc_id = get_htrc_id(zippath)

    print("Finding frequencies for: {}".format(htrc_id))

    meta = get_meta(htrc_id)
    text = StringIO()

    with ZipFile(zippath, 'r') as zipfile:
        page_files = [zipentry.filename for zipentry in zipfile.infolist() if zipentry.filename.lower().endswith(".txt")]
        for filename in sorted(page_files):
            text.write(u' ')
            text.write(zipfile.read(filename).decode('utf-8'))
    
    text = text.getvalue()

    relfreqs = findrelativefrequencies(text, keywords)
    relfreqs.update(meta)
    relfreqs["VolID"] = htrc_id

    return relfreqs

def processtxtvolume(textpath, keywords):
    root, file = os.path.split(textpath)
    print("Finding frequencies for " + file)

    #single core functionality commented out
    #log_freqs(findrelativefrequencies(textpath), textpath)

    with open(textpath, encoding='utf-8') as textfile:
        text = textfile.read()

    relfreqs = findrelativefrequencies(text, keywords)

    # relfreqs["Title"] =
    # relfreqs["Author"] =
    # relfreqs["Year"] =
    relfreqs["VolID"] = file

    return relfreqs


######## main() ##############

def main():
    starttime = time.time()
    ignorechars = [".", ",", "?", ")", "(", "\"", ":", ";", "'s"]

    parser = argparse.ArgumentParser(
        description='Calculate the frequency of keywords in text files. Creates an output file ranking by relative frequency.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--words', dest='keywordfilename', default='keywords.txt',
                        help='A text file containing the line-break separate keywords to use')
    parser.add_argument('--texts', dest='textdir',  default='texts',
                        help='The folder of the volumes to examine')
    parser.add_argument('--format', dest='fileformat', choices=['txt', 'zip'], default='txt',
                        help='Specifies the format of the volume files')

    args = parser.parse_args()

    textdir = args.textdir
    keywordfilename = args.keywordfilename
    fileformat = args.fileformat

    if not os.path.exists(keywordfilename):
        sys.exit("Invalid keywords file path. Aborting.")
    elif not os.path.exists(textdir):
        sys.exit("Invalid volumes folder path. Aborting.")

    global keywords
    keywords = set()

    print("Reading keywords.")
    with open(keywordfilename, encoding='utf-8') as keywordfile:
        for line in keywordfile.readlines():
            words = line.lower().split()
            if not words: continue
            keywords.add(tuple(words))
    print("Keywords read: {}".format(len(keywords)))

    global tokens
    tokens = set(token for keyword in keywords for token in keyword)

    print("Reading volume files.")
    index = 0
    filecount = 0

    pool = Pool()
    with open('output.csv', 'wb') as csvfile:
        global outputcsv
        outputcsv = csv.writer(csvfile)
        outputcsv.writerow(["Filename", "VolID", "Title", "Author", "Year", "WordCount", "RelFreqSum"] + [" ".join(k).encode('utf-8') for k in keywords])

        try:
            for root, dirs, files in os.walk(textdir):
                for volume in [file for file in files if file.lower().endswith("." + fileformat)]:
                    volumepath = os.path.join(root, volume)
                    filecount += 1
                    if bool(regex.search("\.zip$", volume, regex.I)):
                        pool.apply_async(processzipvolume, (volumepath,), callback=partial(log_freqs, file=volumepath))
                    elif bool(regex.search("\.txt$", volume, regex.I)):
                        pool.apply_async(processtxtvolume, (volumepath,), callback=partial(log_freqs, file=volumepath))
        finally:
            pool.close()
            pool.join()

    print("Files processed: {}".format(filecount))

    elapsed = int(time.time() - starttime)
    print("Time elapsed: {}".format(timedelta(seconds=elapsed)))

if __name__ == '__main__':
    main()
