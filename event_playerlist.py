#this is a shortening of the previous version that did decklists + players all at once.

import urllib2
import pandas as pd
from sys import argv

# --- here's the static data we need: info about MP-PP conversions and cash --- #
gpppdict = { 30:1, 31:1, 32:1, 33:2, 34:2, 35:2, 36:3, 37:3, 38:3, 39:4, 40:4, 41:4, 42:4, 43:4, 44:4, 45:4 }
gpcash = [10000, 5000] + [2500]*2 + [1500]*4 + [1000]*8 + [500]*16 + [250]*32
ptppdict = {0: 3, 1: 3, 2: 3, 3: 3, 4: 3, 5: 3, 6: 3, 7: 3, 8: 3, 9: 3, 10: 3, 11: 3, 12: 3, 13: 3, 14: 3, 15: 3, 16: 3, 17: 3, 18: 3, 19: 3, 20: 3, 21: 3, 22: 3, 23: 3, 24: 3, 25: 3, 26: 3, 27: 4, 28: 5, 29: 5, 30: 6, 31: 7, 32: 8, 33: 10, 34: 11, 35: 12, 36: 15, 37: 15, 38: 15, 39: 15, 40: 15, 41: 15, 42: 15, 43: 15, 44: 15, 45: 15}
ptcash = [50000, 20000, 15000, 12500, 10000, 9000, 7500, 6000] + [5000]*8 + [3000]*8 + [2000]*8 + [1500]*16 + [1000]*16
wcppdict = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 1, 13: 1, 14: 1, 15: 2, 16: 2, 17: 2, 18: 3, 19: 3, 20: 3, 21: 4, 22: 4, 23: 4, 24: 5, 25: 5, 26: 5, 27: 6, 28: 6, 29: 6, 30: 7, 31: 7, 32: 7, 33: 8, 34: 8, 35: 8, 36: 9, 37: 9, 38: 9, 39: 10, 40: 10, 41: 10, 42: 11}
wccash = [100000, 50000] + [25000]*2 + [10000]*4 + [5000]*8 + [2500]*8
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
	It returns a pandas dataframe with the standings as of round 15.

	If you want to work with the pandas dataframe, run this file within a Python session
	and set the write variable to False.
	"""
	url = "http://magic.wizards.com/en/events/coverage/%s//tournament-results" %(event)
	page = urllib2.urlopen(url)
	lines = page.readlines()
	r15url = getRound15URL(lines, event)
	top8 = round16(lines, event)
	playerlist = rawresults(r15url, event)
	resultsdf = compileResults(top8, playerlist, event)

	#converting to JSON as output. we always output the standings.
	if write:
		js1 = file("%s_standings.json" %(event), 'w')
		js1.write(resultsdf.to_json())

	#if write = False, give back dataframes instead of writing
	else:
		return resultsdf

def getRound15URL(source, gp):
	"""
	Input a GP code, output a URL linking to the round 15/16 standings for GP/PTs.
	As of mid-2017 every round 15 has the same basic URL, but we'll get there through the
	coverage page in case R15 hasn't been posted yet.
	"""
	#this could be zero but it would be pretty weird if it were more than 2
	if gp[:2] == "pt": lastround = 16
	elif gp[-2:] == "wc": lastround = 14
	else: assert gp[:2] == "gp"; lastround = 15
	r15line = [l for l in source if "round-%d-standings" %(lastround) in l]
	if len(r15line) == 1:
		x = r15line[0].split('href="')
		for piece in x:
			if "round-%d-standings" %(lastround) in piece:
				return piece.split('"')[0]
	raise IndexError("Error 1: Couldn\'t find link to R15 standings")

def rawresults(r15url, event, offset=4):
	"""
	This function reads the source code and returns people who earned a pro point.
	It used to be that consecutive names were 5 lines apart, but the modern template is 4.
	Still, I've softcoded "offset" in case something changes in the source code.
	"""
	page = urllib2.urlopen(r15url)
	lines = page.readlines()
	playerlist = []
	st = [i for i in range(len(lines)) if "sortable-table" in lines[i]]
	if len(st) != 1: #there is a possible fail case here if an old version of WER is used
		return rawresults2(r15url, event, offset)
	#the first-place name is predictably six lines after the start of the table
	i = st[0] + offset+1
	while "<td" in lines[i]:
		place = getPlace(lines[i-1])
		name = getName(lines[i])
		pts = getMP(lines[i+1])
		i += offset
		if event[:2] == "gp":
			if pts >= 30 or place <= 8: #can you top 8 with less than 30MP? ah whatever
				playerlist.append([place, name, pts])
		elif event[:2] == "pt" or event[-2:].lower() == "wc":
			playerlist.append([place, name, pts])
	return playerlist

def rawresults2(r15url, event, offset=4):
	"""
	If the source code is generated from an older version of the score reporter,
	we'll wind up using this function to figure out the round 15 results.
	"""
	page = urllib2.urlopen(r15url)
	lines = page.readlines()
	playerlist = []
	tbodies = [i for i in range(len(lines)) if "<tbody>" in lines[i]]
	if len(tbodies) != 1:
		raise AssertionError("Error 2: Exhausted methods to find R15 standings")
	i = tbodies[0] + offset
	while "<td" in lines[i]:
		place = getPlace(lines[i])
		name = getName(lines[i+1])
		pts = getMP(lines[i+2])
		i += offset
		if event[:2] == "gp":
			if pts >= 30 or place <= 8: #can you top 8 with less than 30MP? ah whatever
				playerlist.append([place, name, pts])
		elif event[:2] == "pt":
			playerlist.append([place, name, pts])
	return playerlist

def compileResults(top8results, playerlist, event):
	"""
	This function processes the final standings and returns a dataframe with
	relevant results data in it. It takes as input the playerlist from rawresults and
	the top8 data as compiled by round16.
	"""
	finishorder = arrange(top8results, playerlist[:8])
	df = pd.DataFrame.from_records(finishorder + playerlist[8:], columns=["place", "name", "MP"], index="place")
	#now to add in pro points.
	if event[:2] == "gp":
		df["PP"] = df["MP"].map(gpppdict)
		df.at[1, "PP"] = 8
		df.at[2, "PP"] = 6
		for i in [3, 4]: df.at[i, "PP"] = 5
		for i in [5, 6, 7, 8]: df.at[i, "PP"] = 4
		df["cash"] = gpcash + [0]*(len(df) - len(gpcash))
	elif event[:2] == "pt":
		df["PP"] = df["MP"].map(ptppdict)
		df.at[1, "PP"] = 30
		df.at[2, "PP"] = 26
		df.at[3, "PP"] = 24
		df.at[4, "PP"] = 22
		df.at[5, "PP"] = 20
		df.at[6, "PP"] = 18
		df.at[7, "PP"] = 17
		df.at[8, "PP"] = 16
		df["cash"] = ptcash + [0]*(len(df) - len(ptcash))
	elif event[:-2].lower() == "wc":
		df["PP"] = df["MP"].map(wcppdict)
		df.at[1, "PP"] = df.at[1, "PP"] + 4
		df.at[2, "PP"] = df.at[2, "PP"] + 2
		df["cash"] = wccash
	return df

def round16(lines, gp):
	"""
	Finds and scrapes the top 8 bracket.
	This code is adapted from the Elo project bracket-reading script.
	This function returns a list of (round, p1, result, p2) tuples.
	"""
	output = []
	
	qf = [i for i in range(len(lines)) if 'bracket q' in lines[i]]
	sf = [i for i in range(len(lines)) if 'bracket s' in lines[i]]
	ff = [i for i in range(len(lines)) if 'bracket f' in lines[i]]
	assert len(qf) <= 1; assert len(sf) <= 1; assert len(ff) <= 1
	sfline, ffline = sf[0], ff[0]
	
	if gp[-2:].lower() != "wc":
		qfline = qf[0]
		QFplayers = [i for i in range(qfline, sfline) if ")" in lines[i]]
		assert len(QFplayers) == 8
		for i in range(4):
			pAline, pBline = lines[QFplayers[2*i]], lines[QFplayers[2*i+1]]
			if "<strong>" in pAline:
				result = "Won"
				pA = namify(pAline.split(") ")[1].split(",")[0].strip())
				pB = namify(pBline.split(") ")[1].split("<")[0].strip())
			else:
				assert "<strong>" in pBline
				result = "Lost"
				pB = namify(pBline.split(") ")[1].split(",")[0].strip())
				pA = namify(pAline.split(") ")[1].split("<")[0].strip())
			matchdata = ("Q", pA, result, pB)
			output.append(matchdata)

	SFplayers = [i for i in range(sfline, ffline) if ")" in lines[i]]
	assert len(SFplayers) == 4
	for i in range(2):
		pAline, pBline = lines[SFplayers[2*i]], lines[SFplayers[2*i+1]]
		if "<strong>" in pAline:
			result = "Won"
			pA = namify(pAline.split(") ")[1].split(",")[0].strip())
			pB = namify(pBline.split(") ")[1].split("<")[0].strip())
		else:
			assert "<strong>" in pBline
			result = "Lost"
			pB = namify(pBline.split(") ")[1].split(",")[0].strip())
			pA = namify(pAline.split(") ")[1].split("<")[0].strip())
		matchdata = ("S", pA, result, pB)
		output.append(matchdata)

	FFplayers = [i for i in range(ffline, ffline+20) if ")" in lines[i]]
	assert len(FFplayers) == 2
	for i in range(1):
		pAline, pBline = lines[FFplayers[2*i]], lines[FFplayers[2*i+1]]
		if "<strong>" in pAline:
			result = "Won"
			pA = namify(pAline.split(") ")[1].split(",")[0].strip())
			pB = namify(pBline.split(") ")[1].split("<")[0].strip())
		else:
			assert "<strong>" in pBline
			result = "Lost"
			pB = namify(pBline.split(") ")[1].split(",")[0].strip())
			pA = namify(pAline.split(") ")[1].split("<")[0].strip())
		matchdata = ("F", pA, result, pB)
		output.append(matchdata)
	return output

# ***--- these helper functions are for reading the R15 standiings ---***

def getPlace(line):	return int(line.strip().split("<td>")[1].split("<")[0])

def getMP(line): return int(line.strip().split("</td>")[0].split(">")[1])

def getName(line):
	rawname = line.strip().split("</td>")[0].split(">")[1]
	#there are three things we need to clear out: country, top 25, and team name (at PTs)
	#first, the country code, which in modern tournaments is two characters.
	#this is a little heavy-handed and will break if "[" appears in the name itself
	if "[" in rawname: rawname = rawname.split("[")[0]
	#next, the top 25. this will be at the beginning, so in the first 5 characters
	if ")" in rawname[:5]: rawname = rawname[rawname.index(")")+1:].strip()
	#finally the team name, if it exists. unfortunately this isn't kind to "Yang, Xiao Yu (Roy)"
	if ")" in rawname: rawname = rawname.split(" (")[0]
	return swapChars(rawname.strip())


# ***--- these functions are for the top 8 bracket ---***

def namify(name):
	name.replace("</a>", '').replace("</strong>", "")
	if len(name.split()) == 2:
		return "%s, %s" %(name.split()[1], name.split()[0])
	else:
		return name

def arrange(top8results, playerlist):
	#top8results are the matches from the top8, playerlist is the list of seeds
	#first we need to figure out who lost in which round of the top 8
	correctstands = [] #eventually we'll return this, but we have to populate it
	qfs, sfs, fin, win = [], [], [], []
	quarters = top8results[0:4]
	semis = top8results[4:6]
	finals = top8results[6]
	if finals[2] == "Won": win.append(finals[1]); fin.append(finals[3])
	else: win.append(finals[3]); fin.append(finals[1])
	for match in semis:
		if match[2] == "Won": sfs.append(match[3])
		else: sfs.append(match[1])
	for match in quarters:
		if match[2] == "Won": qfs.append(match[3])
		else: qfs.append(match[1])

	#okay, now we have to arrange the results to match the standings
	#the problem is that the standings are "last, first" and the top8 bracket isn't
	#so the plan is to sort all the characters in each name to get something uniform
	#if two people who anagram to each other make the top 8, ya got me. this will break
	#it's possible a name in the top 8 bracket won't match a name in the standings.
	#if that happens i'm going to take "closest possible", based on the number of
	#matching characters. if something weird happened (post-round 15 DQ?) this won't work

	namedict = {entry[1] : entry for entry in playerlist} #now name : (place,name,mp)
	placementdict = {}
	for top8name in sum([qfs, sfs, fin, win], []):
		for name in namedict:
			if melt(top8name) == melt(name): placementdict[top8name] = namedict[name]
		if top8name not in placementdict: #didn't find exact match
			standingsname = closestName(namedict.keys(), top8name)
			placementdict[top8name] = namedict[standingsname]

	#now we make the winner be #1, the finalist #2...
	winnerentry = placementdict[win[0]]
	correctstands.append([1, winnerentry[1], winnerentry[2]])

	finalistentry = placementdict[fin[0]]
	correctstands.append([2, finalistentry[1], finalistentry[2]])
	#sort the semifinalists bsaed on r15 standings, then 3 and 4
	sfsorted = sorted([placementdict[name] for name in sfs], entrysort)
	for i in range(len(sfsorted)):
		entry = sfsorted[i]
		correctstands.append([i+3, entry[1], entry[2]])
	#sort the quarterfinalists and get 5 6 7 8.
	qfsorted = sorted([placementdict[name] for name in qfs], entrysort)
	for i in range(len(qfsorted)):
		entry = qfsorted[i]
		correctstands.append([i+5, entry[1], entry[2]])
	return correctstands

def melt(name):
	return reduce(lambda a, b: a+b, sorted([ch for ch in name if ch.isalpha()]))
	
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

def entrysort(e1, e2): return cmp(e1[0], e2[0])

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
		print "This file will create [event]_standings.json in its directory when run."
