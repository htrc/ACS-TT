from __future__ import print_function
from operator import itemgetter
from multiprocessing import Pool
from functools import partial
from contextlib import closing
from zipfile import ZipFile
from xml.etree.ElementTree import ElementTree
from urllib import quote

import sys, os, argparse, time, csv, re, urllib2, json

METS_NS = { "METS": "http://www.loc.gov/METS/", "PREMIS": "info:lc/xmlns/premis-v2" }
SOLR_QUERY_TPL = "http://chinkapin.pti.indiana.edu:9994/solr/meta/select?q=id:{}&fl=title,author,publishDate&wt=json"

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
    relfrequencies[file] = result

def get_htrc_id(zippath):
    folder, zipfile = os.path.split(zippath)
    metsfile = os.path.splitext(zipfile)[0] + ".mets.xml"
    metspath = os.path.join(folder, metsfile)
    metsxml = ElementTree(file=metspath)
    htrc_id = metsxml.find(".//PREMIS:objectIdentifierValue", METS_NS).text

    return htrc_id

def get_meta(htrc_id):
    meta = {}
    query = SOLR_QUERY_TPL.format(quote(htrc_id))
    url = urllib2.urlopen(query)
    try:
        response = json.loads(url.read())
        doc = response["response"]["docs"][0]
        meta["Title"] = "\n".join(doc["title"])
        meta["Author"] = "\n".join(doc["author"])
        meta["Year"] = "\n".join(doc["publishDate"])
    finally:
        url.close()

    return meta

def processzipvolume(zippath, keywords):
    root, file = os.path.split(zippath)

    htrc_id = get_htrc_id(zippath)
    meta = get_meta(htrc_id)

    print("Finding frequencies for " + file)

    text = ""

    with ZipFile(zippath) as zipfile:
        for filename in [zipentry.filename for zipentry in zipfile.infolist() if zipentry.filename.lower().endswith(".txt")]:
            text += "\n" + zipfile.read(filename)

    relfreqs = findrelativefrequencies(text, keywords)
    relfreqs.update(meta)

    return relfreqs

def processtxtvolume(textpath, keywords):
    root, file = os.path.split(textpath)
    print("Finding frequencies for " + file)

    #single core functionality commented out
    #log_freqs(findrelativefrequencies(textpath), textpath)

    with open(textpath) as textfile:
        text = textfile.read().lower()

    relfreqs = findrelativefrequencies(text, keywords)

    relfreqs["Title"] = "temp"
    relfreqs["Author"] = "temp"
    relfreqs["Year"] = "temp"

    return relfreqs

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
relfrequencies = {}

print("Reading keywords.")
with open(keywordfilename) as keywordfile:
    for line in keywordfile.readlines():
        keywords.append(line.strip(' \t\n\r').lower())
print("Keywords read: {}".format(len(keywords)))

print("Reading volume files.")
index = 0

pool = Pool()
try:
    for root, dirs, files in os.walk(textdir):
        for volume in [file for file in files if file.lower().endswith("." + fileformat)]:
            volumepath = os.path.join(root, volume)
            if bool(re.search("\.zip$", volume, re.I)):
                pool.apply_async(processzipvolume, (volumepath, keywords,), callback=partial(log_freqs, file=volumepath))
            elif bool(re.search("\.txt$", volume, re.I)):
                pool.apply_async(processtxtvolume, (volumepath, keywords,), callback=partial(log_freqs, file=volumepath))
finally:
    pool.close()
    pool.join()

print("Volume files read: {}".format(len(relfrequencies)))
print("Writing output.csv")

with open('output.csv', 'w') as csvfile:
    outputcsv = csv.writer(csvfile)
    outputcsv.writerow(["Filename", "Title", "Author", "Year", "WordCount", "RelFreqSum"] + keywords)

    # TODO: Sort by relfreq first
    for filepath, relfrequency in relfrequencies.items():
        # TODO: Title, Author, etc.
        sortedfreqs = []
        for keyword in keywords:
            sortedfreqs.append(relfrequency["Frequencies"][keyword])

        outputcsv.writerow(
            [filepath,
             relfrequency["Title"],
             relfrequency["Author"],
             relfrequency["Year"],
             relfrequency["WordCount"],
             relfrequency["RelFreqSum"]
            ] + sortedfreqs)

print("Time elapsed: {} seconds".format(time.time() - starttime))
