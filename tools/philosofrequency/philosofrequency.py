from __future__ import print_function
from operator import itemgetter
from multiprocessing import Pool
from functools import partial
from contextlib import closing
from zipfile import ZipFile
from urllib import quote
from urllib2 import Request, urlopen, URLError, HTTPError
from pairtree import pairtree_path
from io import open

import sys, os, argparse, time, csv, re, json

SOLR_QUERY_TPL = "http://chinkapin.pti.indiana.edu:9994/solr/meta/select?q=id:{}&fl=title,author,publishDate&wt=json&omitHeader=true"
PAIRTREE_REGEX = re.compile(r"(?P<libid>[^/]+)/pairtree_root/(?P<ppath>.+)/(?P<cleanid>[^/]+)\.[^.]+$")

def findrelativefrequencies(text, keywords):
    textfreqs = {}
    relfreqs = {}

    for keyword in keywords:
        textfreqs[keyword] = 0

    words = text.split()

    for word in words:
        for ignore in ignorechars:
            if ignore in word:
                word = word.replace(ignore, "")
        if word in keywords:
            textfreqs[word] += 1

    wordcount = len(words)
    relfreqs["WordCount"] = wordcount

    relfreqtotal = 0
    for key, value in textfreqs.items():
        relfreqtotal += float(value) / float(wordcount)
#        relfreqs[key] = float(relfreqtotal)

    relfreqs["RelFreqSum"] = relfreqtotal
    relfreqs["Frequencies"] = textfreqs

    return relfreqs

def log_freqs(result, file, ):
    # TODO: Title, Author, etc.
    sortedfreqs = []
    for keyword in keywords:
        sortedfreqs.append(result["Frequencies"][keyword])

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
        ] + sortedfreqs)

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
        response = json.loads(url.read().decode("utf-8"))["response"]
        url.close()
        numFound = response["numFound"]
        if numFound == 0:
            print("{}: No metadata found in SOLR.".format(htrc_id))
        else:
            if numFound > 1:
                print("{}: {} metadata records were found - using the first result.".format(htrc_id, numFound))
            doc = response["docs"][0]
            meta["Title"] = "; ".join(doc["title"])
            meta["Author"] = "; ".join(doc["author"])
            meta["Year"] = "; ".join(doc["publishDate"])

    return meta

def processzipvolume(zippath):
    root, file = os.path.split(zippath)

    htrc_id = get_htrc_id(zippath)
    meta = get_meta(htrc_id)

    print("Finding frequencies for: " + htrc_id)

    text = ""

    with ZipFile(zippath, 'r') as zipfile:
        for filename in [zipentry.filename for zipentry in zipfile.infolist() if zipentry.filename.lower().endswith(".txt")]:
            text += "\n" + zipfile.read(filename).decode("utf-8")

    relfreqs = findrelativefrequencies(text, keywords)
    relfreqs.update(meta)
    relfreqs["VolID"] = htrc_id

    return relfreqs

def processtxtvolume(textpath):
    root, file = os.path.split(textpath)
    print("Finding frequencies for " + file)

    #single core functionality commented out
    #log_freqs(findrelativefrequencies(textpath), textpath)

    with open(textpath, encoding='utf-8') as textfile:
        text = textfile.read().lower()

    relfreqs = findrelativefrequencies(text, keywords)

    # relfreqs["Title"] =
    # relfreqs["Author"] =
    # relfreqs["Year"] =
    relfreqs["VolID"] = file

    return relfreqs

def pretty_time(seconds):
    sign_string = '-' if seconds < 0 else ''
    seconds = abs(int(seconds))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days > 0:
        return '%s%dd%dh%dm%ds' % (sign_string, days, hours, minutes, seconds)
    elif hours > 0:
        return '%s%dh%dm%ds' % (sign_string, hours, minutes, seconds)
    elif minutes > 0:
        return '%s%dm%ds' % (sign_string, minutes, seconds)
    else:
        return '%s%ds' % (sign_string, seconds)

######## main() ##############

starttime = time.time()
ignorechars = [".",",","?",")","(","\"",":",";","'s"]

parser = argparse.ArgumentParser(
    description='Calculate the frequency of keywords in text files. Creates an ouput file ranking by relative frequency.',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)
parser.add_argument('--words', dest='keywordfilename', default='keywords.txt',
                    help='A text file containing the line-break separate keywords to use')
parser.add_argument('--texts', dest='textdir',  default='texts',
                    help='The folder of the volumes to examine')
parser.add_argument('--format', dest='fileformat', metavar='txt|zip', default='txt',
                    help='Specifies the format of the volume files')

args = parser.parse_args()

textdir = args.textdir
keywordfilename = args.keywordfilename
fileformat = args.fileformat

if fileformat not in ["txt", "zip"]:
    sys.exit("Invalid file format specified. Aborting.")
if not os.path.exists(keywordfilename):
    sys.exit("Invalid keywords file path. Aborting.")
elif not os.path.exists(textdir):
    sys.exit("Invalid volumes folder path. Aborting.")

keywords = []

print("Reading keywords.")
with open(keywordfilename, encoding='utf-8') as keywordfile:
    for line in keywordfile.readlines():
        keywords.append(line.strip(' \t\n\r').lower())
print("Keywords read: {}".format(len(keywords)))

print("Reading volume files.")
index = 0
filecount = 0

pool = Pool()
with open('output.csv', 'wb') as csvfile:
    outputcsv = csv.writer(csvfile)
    outputcsv.writerow(["Filename", "VolID", "Title", "Author", "Year", "WordCount", "RelFreqSum"] + [k.encode('utf-8') for k in keywords])

    try:
        for root, dirs, files in os.walk(textdir):
            for volume in [file for file in files if file.lower().endswith("." + fileformat)]:
                volumepath = os.path.join(root, volume)
                filecount += 1
                if bool(re.search("\.zip$", volume, re.I)):
                    pool.apply_async(processzipvolume, (volumepath,), callback=partial(log_freqs, file=volumepath))
                elif bool(re.search("\.txt$", volume, re.I)):
                    pool.apply_async(processtxtvolume, (volumepath,), callback=partial(log_freqs, file=volumepath))
    finally:
        pool.close()
        pool.join()

print("Files processed: {}".format(filecount))

elapsed = int(time.time() - starttime)
print("Time elapsed: {}".format(pretty_time(elapsed)))
