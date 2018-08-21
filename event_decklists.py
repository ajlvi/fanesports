#version 18.08.11. 
#This is a stripped-down version of the previous file which did both standings and
#decklists. Since it no longer uses the standings, some parts of the code have been
#deleted to streamline it.

import urllib2
import pandas as pd
from sys import argv

specialChars = { "&agrave;":"a", "&egrave;":"e", "&Egrave;":"E", "&igrave;":"i",\
"&ograve;":"o", "&ugrave;":"u", "&yacute;":"y", '&ccedil;':'c', "&eth;": "d", \
"&aacute;":"a", "&eacute;":"e", "&iacute;":"i", "&oacute;":"o", "&uacute;":"u",\
"&Aacute;":"A", "&Eacute;":"E", "&Iacute;":"I", "&Oacute;":"O", "&yuml;":"y", \
"&auml;":"a", "&euml;":"e", "&iuml;":"i", "&ouml;":"o", "&uuml;":"u", "&Ouml;":"O",\
"&acirc;":"a","&ecirc;":"e", "&icirc;":"i","&ocirc;":"o", "&ucirc;":"u", \
"&Acirc;":"A", "&not;":"", "&aring;":"a", "&oslash;":"o", "&Oslash;":"O",\
"&szlig;":"ss", "&AElig;":"ae", "&aelig;":"ae", "&scaron;":"s", "&Scaron;":"S", "&#367;":"u",\
"&atilde;":"a", "&Atilde;":"a", "&ntilde;":"n", "&otilde;":"o", "&oelig;":"oe", "&rsquo;":"'"}

def acquireInfo(event, write=True):
	"""
	This is the high-level function meant to be run by the user.
	It returns a pandas dataframes with all the cards in the top 8 decklists.
	The names of the pilots are included but aren't cross-referenced against the standings.

	If you want to work with the pandas dataframe, run this file within a Python session
	and set the write variable to False.
	"""
	url = "http://magic.wizards.com/en/events/coverage/%s//tournament-results" %(event)
	page = urllib2.urlopen(url)
	lines = page.readlines()
	cardlist = rawdecklists(lines)
	decksdf = compileDecklists(cardlist)

	#converting to JSON as output.
	#note this currently will NOT output anything if the GP is not constructed.
	if write:
		if decksdf[decksdf["name"] == decksdf["name"].unique()[0]]["copies"].sum() >= 75:
			js2 = file("%s_decklists.json" %(event), 'w')
			js2.write(decksdf.to_json())

	#if write = False, give back dataframes instead of writing
	else:
		return decksdf
#!!		return resultsdf, decksdf

def rawdecklists(source):
	"""
	This function reads the source code and outputs the eight decklists from the top 8.
	"""
	starts = [i for i in range(len(source)) if "sorted-by-overview" in source[i]]
	ends = [i for i in range(len(source)) if "sorted-by-color-container" in source[i]]
	assert len(starts) == len(ends) #at least this much should be true
	cards = []
	for i in range(len(starts)):
		location = "main"
		startno = starts[i]
		endno = ends[i] #the cards in the decklist are between startno and endno
		pilot =  swapChars(getPilotName(source[startno - 28]))
		j = startno
		while j < endno:
			if "card-count" in source[j]:
				copies, cardname = getCopies(source[j]), getCardname(source[j+1])
				cards.append((pilot, copies, cardname, location))
			elif "Sideboard" in source[j]: location = "side"
			j += 1
	return cards

def compileDecklists(cards):
	"""
	This function cross-references the decklists with the standings to figure out
	the placement of everyone in the top 8, then returns a dataframe.
	All of this is unnecessary in the current version. I'm marking the parts
	that have been bulldozed by "#!!".
	"""
	df = pd.DataFrame.from_records(cards, columns=["name", "copies", "card", "location"])
#!!	finishorder = arrange(top8results, playerlist[:8])
#!!	namedict = {melt(entry[1]) : entry[0] for entry in finishorder } # now a dict of name:place
#!!	#here we figure out the placement of the people. similar to the top 8 bracket.
#!!	#i'm praying that the names that appear attached to the decklists match those
#!!	#that are in the standings. also that two anagrams never make the same top 8.
#!!	placementdict = {}
#!!	for pilot in df["name"].unique():
#!!		for name in namedict:
#!!			if melt(pilot) == melt(name): placementdict[pilot] = namedict[name]
#!!		if pilot not in placementdict: #didn't find exact match
#!!			standingsname = closestName(namedict.keys(), pilot)
#!!			placementdict[pilot] = namedict[standingsname]
#!!	df["place"] = df["name"].map(placementdict)
	return df


# ***--- these functions are for the decklists ---***

def getPilotName(line):
	try:
		assert "<h4>" in line
	except AssertionError:
		raise AssertionError("Error 4: Pilot's line isn't 28 lines above deck start")
	if "&rsquo;" in line: return line.split("&rsquo;")[0].split("<h4>")[1]
	elif "'s " in line: return line.split("'s ")[0].split("<h4>")[1]
	elif "' " in line: return line.split("' ")[0].split("<h4>")[1]
	elif " - " in line: return line.split(" - ")[0].split("<h4>")[1]
	else: #likely a limited GP, so this isn't too important
		return line.split("<h4>")[1].split("</h4>")[0]

def getCopies(line):
	return int(line.split("count\">")[1].split("</span>")[0])

def getCardname(line):
	return line.split("list-link\">")[1].split("</a>")[0]

# needed --- ?
def nearness(name1, name):
	name1_melt = melt(name1).upper()
	name_melt = melt(name).upper()
	matched = 0
	for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
		matched += min( [name1_melt.count(ch), name_melt.count(ch) ] )
	return float(matched)/len(name_melt)

def closestName(list1, name):
	"""
	list1 comes from the standings. name comes from the top8 bracket or the list of
	decklist pilots. If there's wasn't an exact match, this finds the closest one
	based on number of matching characters.
	"""
	scores = sorted( [(nearness(a, name), a) for a in list1], reverse=True )
	return scores[0][1]

def swapChars(key):
	"""
	This function replaces special HTML characters with ASCII equivalents.
	(It is as thorough as the specialChars dictionary is above, that is, kind of thorough?)
	"""
	for ch in specialChars:
		key = key.replace(ch, specialChars[ch])
	return key
	
if __name__ == '__main__':
	if len(argv) == 2: acquireInfo(argv[1])
	else:
		print "Syntax for usage: python pascal.py [event]"
		print "This file will create [event]_decklists.json in its directory when run."
