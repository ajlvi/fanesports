import urllib2
import pandas as pd
from sys import argv

def players_with_pp(write=True):
	"""
	Scrapes the Premier Play leaderboard and outputs a .json file with its information.
	What's kept is name, nationality, pro points at the moment.

	IMPORTANT: The leaderboard's URL is hardcoded! When the season changes you have to change it.

	If the underlying dataframe is ever of value, changing write to False will output the df.
	"""
	url = "https://magic.wizards.com/en/events/coverage/top-players/statistics/2017-18-leaderboard"
	page = urllib2.urlopen(url)
	lines = page.readlines()
	table_line = [i for i in range(len(lines)) if "sortable-table" in lines[i]]
	assert len(table_line) == 1
	i = table_line[0]
	player_data = []
	#now to jump to the first player on the list
	while "</tr><tr" not in lines[i]: i += 1
	while "</tbody>" not in lines[i]:
		firstname = tdsplit(lines[i+1])
		lastname = tdsplit(lines[i+2])
		country = tdsplit(lines[i+3])
		PPtotal = int(tdsplit(lines[i+5]))
		name = "%s, %s" %(lastname, firstname)
		player_data.append([name, country, PPtotal])
		i += 17
	df = pd.DataFrame.from_records(player_data, columns=["name", "country", "PP"])
	if write:
		df.to_json("players_with_pp.json")
	else:
		return df

def qualified_for_PT(pt, write=True):
	"""
	Scrapes the PT invitation list and outputs a .json file with its contents.
	What's kept is name, invitation source, event city, event date.

	I'm only 60% sure that the URL shell is correct -- it seems to have worked for PTXLN and PTRIX.
	If it's not then the first like below will need to be manually updated.

	If the underlying dataframe is ever of value, changing write to False will output the df.
	"""
	url = "https://magic.wizards.com/en/events/premierplay/protour/%s/invitations" %(pt)
	page = urllib2.urlopen(url)
	lines = page.readlines()
	table_line = [i for i in range(len(lines)) if "sortable-table" in lines[i]]
	assert len(table_line) == 1
	i = table_line[0]
	player_data = []
	#now to jump to the first player on the list
	while "</tr><tr" not in lines[i]: i += 1
	while "</tbody>" not in lines[i]:
		firstname = tdsplit2(lines[i])
		lastname = tdsplit(lines[i+1])
		name = "%s, %s" %(lastname, firstname)
		qmethod = tdsplit(lines[i+2])
		eventdate = tdsplit(lines[i+3])
		eventcity = tdsplit(lines[i+4])
		player_data.append([name, qmethod, eventcity, eventdate])
		i += 6
	df = pd.DataFrame.from_records(player_data, columns=["name", "qual_method", "event_city", "event_date"])
	if write:
		df.to_json("%s_invites.json" %(pt))
	else:
		return df

def tdsplit(line): return line.split(">")[1].split("<")[0]
def tdsplit2(line): return line.split(">")[-2].split("<")[0]

if __name__ == "__main__":
	if len(argv) >= 2:
		if argv[1] == "1": players_with_pp()
		elif argv[1] == "2":
			if len(argv) >= 3: qualified_for_PT(argv[2])
	else:
		print "Syntax for usage: python propoints.py [OPTION] [PTCODE]"
		print "[OPTION] can be either 1 or 2."
		print "1: Scrape the Premier Play leaderboard for everyone with 1+ PP this season."
		print "2: Scrape the invitation list for a PT. This requires the ptcode."
		print "Example:  python propoints.py 2 ptrix  "
