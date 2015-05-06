from __future__ import print_function
from operator import itemgetter
from multiprocessing import Pool
from functools import partial

import sys, os, argparse, time, csv

starttime = time.time()
ignorechars = [".",",","?",")","(","\"",":",";","'s"]

parser = argparse.ArgumentParser(description='Calculate the frequency of keywords in text files. Creates an ouput file ranking by relative frequency.')
parser.add_argument('--words', dest='keywordfilename', default="keywords.txt",
                   help='A text file containing the line-break separate keywords to use. Defaults to "keywords.txt".')
parser.add_argument('--texts', dest='textdir',  default="texts",
                   help='The folder of text files to examine. Defaults to "texts".')

args = parser.parse_args()

textdir = args.textdir
keywordfilename = args.keywordfilename

if not os.path.exists(keywordfilename):
    sys.exit("Invalid keywords file path. Aborting.")
elif not os.path.exists(textdir):
    sys.exit("Invalid texts file path. Aborting.")
    
keywords = []
relfrequencies = {}

print("Reading keywords.")
keywordfile = open(keywordfilename)
for line in keywordfile.readlines():
    keywords.append(line.strip(' \t\n\r').lower())
keywordfile.close()
print("Keywords read: {}".format(len(keywords)))

# add list of files in folder-of-texts as list
print("Reading text files.")
index = 0

def findrelativefrequencies(textpath):
    print("Finding frequencies " + textpath)
    textfreqs = {}
    relfreqs = {}
    
    for keyword in keywords:
        textfreqs[keyword] = 0
    
    textfile = open(textdir + "/" + textpath)
    text = textfile.read().lower()
    textfile.close()
    
    words = text.split()
    
    for keyword in keywords:
        textfreqs[keyword] = 0
        
    for word in words:
        for ignore in ignorechars:
            if ignore in word:
                word = word.replace(ignore, "")
        if word in keywords:
            textfreqs[word] += 1
    
    wordcount = len(words)

    relfreqs["Title"] = "temp"
    relfreqs["Author"] = "temp"
    relfreqs["Year"] = "temp"
    relfreqs["WordCount"] = wordcount
    
    relfreqtotal = 0
    for key, value in textfreqs.items():
        relfreqtotal += float(value) / float(wordcount)
#        relfreqs[key] = float(relfreqtotal)
        
    relfreqs["RelFreqSum"] = relfreqtotal
    relfreqs["Frequencies"] = textfreqs
    
    return relfreqs

def log_freqs(result, textfile):
    relfrequencies[textfile] = result
    
pool = Pool()
for textpath in os.listdir(textdir):
    #single core functionality commented out
    #log_freqs(findrelativefrequencies(textpath), textpath)
    pool.apply_async(findrelativefrequencies, (textpath,), callback=partial(log_freqs, textfile=textpath))
    
pool.close()
pool.join()

print("Text files read: {}".format(len(relfrequencies)))
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