import urllib2
import pandas as pd
from sys import argv

# --- here's the static data we need: info about MP-PP conversions and cash --- #
specialChars = { "&agrave;":"a", "&egrave;":"e", "&Egrave;":"E", "&igrave;":"i",\
"&ograve;":"o", "&ugrave;":"u", "&yacute;":"y", '&ccedil;':'c', "&eth;": "d", \
"&aacute;":"a", "&eacute;":"e", "&iacute;":"i", "&oacute;":"o", "&uacute;":"u",\
"&Aacute;":"A", "&Eacute;":"E", "&Iacute;":"I", "&Oacute;":"O", "&yuml;":"y", \
"&auml;":"a", "&euml;":"e", "&iuml;":"i", "&ouml;":"o", "&uuml;":"u", "&Ouml;":"O",\
"&acirc;":"a","&ecirc;":"e", "&icirc;":"i","&ocirc;":"o", "&ucirc;":"u", \
"&Acirc;":"A", "&not;":"", "&aring;":"a", "&oslash;":"o", "&Oslash;":"O",\
"&szlig;":"ss", "&AElig;":"ae", "&aelig;":"ae", "&scaron;":"s", "&Scaron;":"S",\
"&atilde;":"a", "&Atilde;":"a", "&ntilde;":"n", "&otilde;":"o", "&oelig;":"oe", "&rsquo;":"'" }

def acquireInfo(event, write=True):
	"""
	This is the high-level function meant to be run by the user.
	It finds the round 1 pairings, creates a list of everyone in the event, and
	writes that list to a .json file [event]_round1.json in its directory.

	If you want to work with the pandas dataframes, run this file within a Python session
	and set the write variable to False. A tuple (resultsdf, decksdf) will be returned.
	"""
	url = "http://magic.wizards.com/en/events/coverage/%s//tournament-results" %(event)
	page = urllib2.urlopen(url)
	lines = page.readlines()
	r1url = getRound1URL(lines)
	playersdf = r1Players(r1url)

	#converting to JSON as output. we always output the playerlists.
	if write:
		js1 = file("%s_round1.json" %(event), 'w')
		js1.write(playersdf.to_json())

	#if write = False, give back dataframe instead of writing
	else:
		return playersdf

def getRound1URL(source):
	"""
	Input a GP code, output a URL linking to the round 1 pairings.
	As of mid-2017 every round 1 has the same basic URL, but we'll get there through the
	coverage page in case R1 hasn't been posted yet.
	"""
	#this could be zero but it would be pretty weird if it were more than 2
	r1line = [l for l in source if "round-1-pairings" in l]
	if len(r1line) == 0:
		raise IndexError("Error 1: Couldn\'t find link to R1 pairings")
	elif len(r1line) > 2:
		print "!! weird behavior: are there two links to the R1 pairings?"
	x = r1line[0].split('href="')
	for piece in x:
		if "round-1-pairings" in piece:
			return piece.split('"')[0]

def r1Players(r1url, offset=6):
	"""
	This function reads the source code and returns everyone in the event.
	The output is a Pandas dataframe with one column so that .to_json will work later.
	"""
	page = urllib2.urlopen(r1url)
	lines = page.readlines()
	playerlist = []
	st = [i for i in range(len(lines)) if "sortable-table" in lines[i]]
	if len(st) == 0:
		raise IndexError("Error 2: No sortable-table in R1 pairings")

	# I admit I'm possibly playing with fire here but for now I feel comfortable
	# hardcoding the position of the first name (as start+offset+1).
	
	i = st[0] + offset + 1
	while "<td" in lines[i]:
		p1 = getName(lines[i])
		p2 = getName(lines[i+3])
		playerlist.append(p1)
		if "BYE" not in p2: playerlist.append(p2)
		i += offset
	print len(playerlist)
	return pd.DataFrame({"player" : playerlist})

# ***--- these helper functions are for reading the R1 pairings ---***

def getName(line):
	rawname = line.strip().split("</td>")[0].split(">")[1]
	#there are three things we need to clear out: country, top 25, and team name (at PTs)
	#the country code tends to be its own cell in the pairings tables, but who knows.
	#first, the country code, which in modern tournaments is two characters.
	#this is a little heavy-handed and will break if "[" appears in the name itself
	if "[" in rawname: rawname = rawname.split("[")[0]
	#next, the top 25. this will be at the beginning, so in the first 5 characters
	if ")" in rawname[:5]: rawname = rawname[rawname.index(")")+1:].strip()
	#finally the team name, if it exists. unfortunately this isn't kind to "Yang, Xiao Yu (Roy)"
	if ")" in rawname: rawname = rawname.split(" (")[0]
	return swapChars(rawname.strip())

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
		print "Syntax for usage: python event_round1.py [event]"
		print "This file will create [event]_round1.json in its directory when run."