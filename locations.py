import requests
from bs4 import BeautifulSoup
import datetime
import os, sys
def removeNonAscii(s): return "".join(filter(lambda x: ord(x)<128, s))


#url = "http://us.megabus.com/default.aspx"
#payload = {"SearchAndBuy1_ddlTravellingTo" : 118, "SearchAndBuy1_ddlLeavingFrom": 101}
#result = requests.get(url, params=payload)
#print removeNonAscii(result.content).encode('ascii', 'ignore')

k = open("codes.txt", 'r')
codes = []
for line in k:
    value, name = line.split(' ', 1)
    codes.append(name.strip())
k.close()

k = open("raw_locations.html", 'r')
p = k.read()
k.close()
ff = BeautifulSoup(p)
i = 0
k = open("locations.txt", 'w')
for f in ff.find_all("select"):
    k.write(codes[i]+":")
    k.write("|".join([str(a.text) for a in f.find_all("option")[1:]])+"\n")
    i+= 1