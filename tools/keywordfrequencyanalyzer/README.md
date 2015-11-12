keywordfrequencyanalyzer.py
===================

What is it?
-----------
Keyword Frequency Analyzer

This script calculates the relative frequencies of a list of keywords. The results can be used to classify documents, given a careful choice of the keywords. The script outputs the frequency of each word, and the sum of relative frequencies of all keywords per text, to a CSV file.

Author(s)
---------
Kevin Schenk, University of Alberta  
Boris Capitanu, HathiTrust Research Center / Illinois Informatics Institute

Requirements
------------
* see `requirements.txt`

Running it
----------
```
usage: keywordfrequencyanalyzer.py [-h] --keywords KEYWORD_FILENAME --output
                                   OUTPUT_FILENAME
                                   (--glob GLOB_PATTERN | --pairtree PAIRTREE_PATH)

Calculate the frequency of keywords in text files. Creates an output file
ranking by relative frequency.

optional arguments:
  -h, --help            show this help message and exit
  --keywords KEYWORD_FILENAME
                        A text file containing the line-break-separated
                        keywords to use (default: None)
  --output OUTPUT_FILENAME
                        The output CSV file (default: None)
  --glob GLOB_PATTERN   A glob pattern specifying the files to process
                        (default: None)
  --pairtree PAIRTREE_PATH
                        The root folder of the HT pairtree hierarchy to
                        process (default: None)
```

Output
------
The data is output as a CSV file. It's not sorted by anything, so I recommend loading it into Excel and sorting it by *RelFreqSum*. This is the sum of the relative frequency of each keyword.

Excel Formula
-------------
An Excel formula that finds the most popular keyword is `=INDEX($G$1:$FVD$1,,MATCH(MAX(G2:FVD2),G2:FVD2,0))`.

G2 corresponds to the first keyword for text 2, while FVK is the last. The column name of the last will determine what this is.

onewordperline.py
=================
Need to get your text file one word per line so you can use it as a keyword file? Run `onewordperline.py input.txt output.txt` on it. This separates each word in the file and removes duplicates, words in a list of stopwords, and words less than three characters long. You might still have to go through them, but it's a start.
