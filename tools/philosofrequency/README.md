philosofrequency.py
===================

What is it?
-----------
Philosophy Keyword Frequency Analyzer

This script attempts to find philosophical texts based on the frequency of a list of keywords. Depending on the keywords, it could potentially be used for other texts. The script outputs the frequency of each word, and the sum of relative frequencies of all keywords per text, to a .csv file.

Author(s)
---------
Kevin Schenk, University of Alberta

Requirements
------------
* https://pypi.python.org/pypi/Pairtree

Running it
----------
You have two options: you can put everything in the same directory as philosofrequency.py, or you can pass the destinations as command line arguments.

1. If you want everything in the same directoy, add your texts to a folder called *texts* in the same directory. Place your keywords file, with each word separated by a line break, and name it *keywords.txt*. This script only works with single word keywords.

2. Otherwise, you can pass the paths as arguments. The keywords file can come after a `--words` flag, and the path to the folder of text files is preceded by `--texts`. So to get the same result as without flags, you'd run `py philosofrequency.py --words keywords.txt --texts texts`

Output
------
The data is output as a csv file. It's not sorted by anything, so I recommend loading it into Excel and sorting it by *RelFreqSum*. This is the sum of the relative frequency of each keyword.

Excel Formula
-------------
An Excel formula that finds the most popular keyword is `=INDEX($G$1:$FVD$1,,MATCH(MAX(G2:FVD2),G2:FVD2,0))`.

G2 corresponds to the first keyword for text 2, while FVK is the last. The column name of the last will determine what this is.

onewordperline.py
-----------------
Need to get your text file one word per line so you can use it as a keyword file? Run `onewordperline.py input.txt output.txt` on it. This separates each word in the file and removes duplicates, words in a list of stopwords, and words less than three characters long. You might still have to go through them, but it's a start.
