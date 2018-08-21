# version 18 June 05 fixing tournament-results URL
import urllib2
import pandas as pd
from sys import argv

# --- here's the static data we need: info about MP-PP conversions and cash --- #
gpppdict = { 30:1, 31:1, 32:1, 33:2, 34:2, 35:2, 36:3, 37:3, 38:3, 39:4, 40:4, 41:4, 42:4, 43:4, 44:4, 45:4 }
gpcash = [10000, 5000] + [2500]*2 + [1500]*4 + [1000]*8 + [500]*16 + [250]*32
ptppdict = {0: 3, 1: 3, 2: 3, 3: 3, 4: 3, 5: 3, 6: 3, 7: 3, 8: 3, 9: 3, 10: 3, 11: 3, 12: 3, 13: 3, 14: 3, 15: 3, 16: 3, 17: 3, 18: 3, 19: 3, 20: 3, 21: 3, 22: 3, 23: 3, 24: 3, 25: 3, 26: 3, 27: 4, 28: 5, 29: 5, 30: 6, 31: 7, 32: 8, 33: 10, 34: 11, 35: 12, 36: 15, 37: 15, 38: 15, 39: 15, 40: 15, 41: 15, 42: 15, 43: 15, 44: 15, 45: 15}
ptcash = [50000, 20000, 15000, 12500, 10000, 9000, 7500, 6000] + [5000]*8 + [3000]*8 + [2000]*8 + [1500]*16 + [1000]*16
specialChars = { "&agrave;":"a", "&egrave;":"e", "&Egrave;":"E", "&igrave;":"i",\
"&ograve;":"o", "&ugrave;":"u", "&yacute;":"y", '&ccedil;':'c', "&eth;": "d", \
"&aacute;":"a", "&eacute;":"e", "&iacute;":"i", "&oacute;":"o", "&uacute;":"u",\
"&Aacute;":"A", "&Eacute;":"E", "&Iacute;":"I", "&Oacute;":"O", "&yuml;":"y", \
"&auml;":"a", "&euml;":"e", "&iuml;":"i", "&ouml;":"o", "&uuml;":"u", "&Ouml;":"O",\
"&acirc;":"a","&ecirc;":"e", "&icirc;":"i","&ocirc;":"o", "&ucirc;":"u", \
"&Acirc;":"A", "&not;":"", "&aring;":"a", "&oslash;":"o", "&Oslash;":"O",\
"&szlig;":"ss", "&AElig;":"ae", "&aelig;":"ae", "&scaron;":"s", "&Scaron;":"S",\
"&atilde;":"a", "&Atilde;":"a", "&ntilde;":"n", "&otilde;":"o", "&oelig;":"oe", "&rsquo;":"'" }

def acquireInfo(event, version=1, write=True):
	"""
	This is the high-level function meant to be run by the user.
	It returns two pandas dataframes: the standings and the cards in the top 8 decklists.
	The top 8 decks get returned regardless of whether you wanted them. For limited events,
	we'll throw that data away after it's acquired.

	If you want to work with the pandas dataframes, run this file within a Python session
	and set the write variable to False. A tuple (resultsdf, decksdf) will be returned.
	"""
	if version == 1:
		url = "http://magic.wizards.com/en/events/coverage/%s//tournament-results" %(event)
	elif version == 2:
		url = "http://magic.wizards.com/en/events/coverage/%s//tournament-results-and-decklists" %(event)
	try:
		page = urllib2.urlopen(url)
	except urllib2.HTTPError: acquireInfo(event, 2, write)
	lines = page.readlines()
	r15url = getRound15URL(lines, event)
	top8 = round16(lines)
	playerlist = rawresults(r15url, top8, event)
	resultsdf = compileResults(top8, playerlist, event)
	cardlist = rawdecklists(lines)
	decksdf = compileDecklists(top8, playerlist, cardlist)

	#converting to JSON as output. we always output the standings.
	if write:
		js1 = file("%s_standings.json" %(event), 'w')
		js1.write(resultsdf.to_json())
	#then we'll check to see if the decks are 75 cards, and if so we'll output decklists
		if decksdf[decksdf["place"] == decksdf["place"].unique()[0]]["copies"].sum() >= 75:
			js2 = file("%s_decklists.json" %(event), 'w')
			js2.write(decksdf.to_json())

	#if write = False, give back dataframes instead of writing
	else:
		return resultsdf, decksdf

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

def rawresults(r15url, top8results, event, offset=4):
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
		return rawresults2(r15url, top8results, event, offset)
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
		elif event[:2] == "pt" or event[-2:] == "wc":
			playerlist.append([place, name, pts])
	return playerlist

def rawresults2(r15url, top8results, event, offset=4):
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
	return df

def round16(lines):
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
	qfline, sfline, ffline = qf[0], sf[0], ff[0]

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

def rawdecklists(source):
	"""
	This function reads the source code and outputs the eight decklists from the top 8.
	"""
	starts = [i for i in range(len(source)) if "sorted-by-overview" in source[i]]
	ends = [i for i in range(len(source)) if "sorted-by-color-container" in source[i]]
	assert len(starts) == 8
	assert len(ends) == 8
	cards = []
	for i in range(8):
		location = "main"
		startno = starts[i]
		endno = ends[i] #the cards in the decklist are between startno and endno

#18 June 04: It has come to my attention that this line is dangerous if the page
#is rendered in a different language (happens by default for unknowable reasons)
#trying to make this a little more robust...
		pilotline = source[startno - 28]
		try:
			assert "<h4" in pilotline
		except AssertionError: #we'll scan for it then...
			i = 32
			pilotline = source[startno - i]
			while i > 24 and "<h4" not in pilotline: i -= 1
		if "<h4" not in pilotline:
			raise ValueError("Error 4: Pilot #%d's name isn't in expected area" %(i+1))

		pilot =  swapChars(getPilotName(pilotline))
		j = startno
		while j < endno:
			if "card-count" in source[j]:
				copies, cardname = getCopies(source[j]), getCardname(source[j+1])
				cards.append((pilot, copies, cardname, location))
			elif "Sideboard" in source[j]: location = "side"
			j += 1
	return cards

def compileDecklists(top8results, playerlist, cards):
	"""
	This function cross-references the decklists with the standings to figure out
	the placement of everyone in the top 8, then returns a dataframe 
	"""
	df = pd.DataFrame.from_records(cards, columns=["name", "copies", "card", "location"])
	finishorder = arrange(top8results, playerlist[:8])
	namedict = {melt(entry[1]) : entry[0] for entry in finishorder } # now a dict of name:place
	#here we figure out the placement of the people. similar to the top 8 bracket.
	#i'm praying that the names that appear attached to the decklists match those
	#that are in the standings. also that two anagrams never make the same top 8.
	placementdict = {}
	for pilot in df["name"].unique():
		for name in namedict:
			if melt(pilot) == melt(name): placementdict[pilot] = namedict[name]
		if pilot not in placementdict: #didn't find exact match
			standingsname = closestName(namedict.keys(), pilot)
			placementdict[pilot] = namedict[standingsname]
	df["place"] = df["name"].map(placementdict)
	return df



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
	name.replace("</a>", '')
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
	
def entrysort(e1, e2): return cmp(e1[0], e2[0])

def swapChars(key):
	"""
	This function replaces special HTML characters with ASCII equivalents.
	"""
	for ch in specialChars:
		key = key.replace(ch, specialChars[ch])
	return key

# ***--- these functions are for the decklists ---***

def getPilotName(line):
#in a previous version I checked for <h4 in this line but it's checked above now.
	if "&rsquo;" in line: return line.split("&rsquo;")[0].split("<h4>")[1]
	elif "'s " in line: return line.split("'s ")[0].split("<h4>")[1]
	elif "' " in line: return line.split("' ")[0].split("<h4>")[1]
	elif " - " in line: return line.split(" - ")[0].split("<h4>")[1]
	elif "&mdash;" in line: return line.split("&mdash;")[0].split("<h4>")[1]
	else: #likely a limited GP, so this isn't too important
		return line.split("<h4>")[1].split("</h4>")[0]

def getCopies(line):
	return int(line.split("count\">")[1].split("</span>")[0])

def getCardname(line):
	return line.split("list-link\">")[1].split("</a>")[0]

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

if __name__ == '__main__':
	if len(argv) == 2: acquireInfo(argv[1])
	else:
		print "Syntax for usage: python pascal.py [GPCODE]"
		print "This file will create one or two .json files in its directory when run."
