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
	It decides if round 4 pairings exist yet and returns True or False as appropriate.
	"""
	url = "http://magic.wizards.com/en/events/coverage/%s//tournament-results" %(event)
	page = urllib2.urlopen(url)
	lines = page.readlines()
	print round4URL(lines)

def round4URL(source):
	"""
	Input a GP code, output whether there's a link to round 4 pairings.
	"""
	#this could be zero but it would be pretty weird if it were more than 2
	r4line = [l for l in source if "round-4-pairings" in l]
	return len(r4line) > 0

if __name__ == '__main__':
	if len(argv) == 2: acquireInfo(argv[1])
	else:
		print "Syntax for usage: python event_round4.py [event]"