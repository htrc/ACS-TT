import sys
from sets import Set

# open input/output files
inputfile = open(sys.argv[1])
outputfile = open(sys.argv[2], 'w')

stopwords = ["the", "and", "for"]
             
my_text = inputfile.read() #reads to whole text file


split_list = sorted(Set(my_text.split()))

split = ""

for word in split_list:
    if len(word) > 2 and word.lower() not in stopwords:
        split += word + "\n"


outputfile.write(split)

inputfile.close()
outputfile.close()