import urllib2
import pandas as pd
from sys import argv

def scrapeSet(set, setcards=[], pagenum=0, write=True):
	"""
	Writes a JSON file with every card in the set. The data kept is
	(cardname, Gatherer ID, collector's number, rarity, set).
	The image URL is recoverable from the Gatherer ID.
	
	The function recursively adds to the initial empty setcards list as it
	traverses search results pages on Gatherer. This gets around the 100 card limit.

	The write variable determines what this function does. By default, write=True
	and a .json file is written. Manually if you set write to False, the function
	will output a pandas dataframe.
	"""
	url = "http://gatherer.wizards.com/Pages/Search/Default.aspx?page=%d&output=checklist&action=advanced&set=+[\"%s\"]" %(pagenum, set.replace(" ", "+"))
#	print url
	page = urllib2.urlopen(url)
	lines = page.readlines()
	cardItems = [i for i in range(len(lines)) if "cardItem" in lines[i]]
	for i in cardItems:
		setcards.append(extractInfo(lines[i]) + (set,))
	controls = [i for i in range(len(lines)) if 'class="pagingcontrols"><a' in lines[i]]
	assert len(controls) <= 1
	if len(controls) == 1: control_line = lines[controls[0]]
	else: #old sets, or supplementary products with < 100 cards
		control_line = ""
	if "page=%d" %(pagenum+1) not in control_line: 
		#this is the fork where we output something
		outframe = pd.DataFrame.from_records(setcards, columns=["cardname", "multiverse_id", "cnum", "rarity", "set"])
		if write: outframe.to_json("%s.json" %(set))
		else: return outframe
	else:
		#there's another page of search results
		return scrapeSet(set, setcards, pagenum+1, write)
		
def extractInfo(line):
	x = line.split("</td>")
	if x[0].split(">")[-1].isdigit():
		collector_no = int(x[0].split(">")[-1])
	else: #old sets don't have numbers!
		collector_no = None
	multiverseID = int(x[1].split("multiverseid=")[1].split('"')[0])
	cardname = x[1].split("</a>")[-2].split(">")[-1]
	rarity = x[4].split("rarity\">")[-1]
	return cardname, multiverseID, collector_no, rarity
	
if __name__ == "__main__":
	if len(argv) == 2: scrapeSet(argv[1])
	else:
		print "Syntax for usage: python gatherer.py [SETNAME]"
		print "The set name is the English set name, *with plus signs for spaces*."
		print "Example:    python gatherer.py Rivals+of+Ixalan"
		print "This file will create one .json file in its directory when run."
