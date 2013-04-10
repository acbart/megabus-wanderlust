import requests
from bs4 import BeautifulSoup
import datetime
def removeNonAscii(s): return "".join(filter(lambda x: ord(x)<128, s))

class Stop(object):
    def __init__(self, date, city, station):
        self.date = date
        self.city = city
        self.station = station
        
    def __str__(self):
        return str(vars(self))
        
class Trip(object):
    def __init__(self, departure, arrival, duration, cost):
        self.departure = departure
        self.arrival = arrival
        self.duration = duration
        self.cost = cost
    def __str__(self):
        return str(vars(self))
        
def search(origin, destination, date):
    url = "http://us.megabus.com/JourneyResults.aspx"
    payload = {"originCode" : str(origin), "destinationCode": str(destination),
               "outboundDepartureDate": str(date), "inboundDepartureDate": "",
               "passengerCount": "1", "transportType": "0",
               "concessionCount": "0", "nusCount": "0",
               "outboundWheelchairSeated": "0", "outboundOtherDisabilityCount": "0",
               "inboundWheelchairSeated": "0", "inboundOtherDisabilityCount": "0",
               "outboundPcaCount": "0", "inboundPcaCount": "0", "promotionCode": "",
               "withReturn": "0"}
    result = requests.get(url, params=payload)
    result = removeNonAscii(result.content).encode('ascii', 'ignore')
    result = BeautifulSoup(result)
    results = []
    for r in result.find_all(class_ = "journey standard"):
        second = r.find(class_ = "two")
        departs = list(second.p.children)
        depart_time = str(departs[2].strip())
        depart_city = str(departs[4].strip())
        depart_station = str(departs[8].strip())
        arrives =  list(second.find(class_ = "arrive").children)
        arrive_time = str(arrives[2].strip())
        arrive_city = str(arrives[4].strip())
        arrive_station = str(arrives[8].strip())
        duration = r.find(class_ = "three").text.strip()
        cost = r.find(class_ = "five").text.strip()
        d = datetime.datetime.strptime(date, "%m/%d/%Y").date()
        dt = datetime.datetime.strptime(depart_time, "%I:%M%p").time() 
        at =  datetime.datetime.strptime(arrive_time, "%I:%M%p").time() 
        depart_time = datetime.datetime.combine(d, dt)
        if at < dt:
            arrive_time = datetime.datetime.combine(d, at) + datetime.timedelta(days=1)
        else:
            arrive_time = datetime.datetime.combine(d, at)
        results.append(Trip(Stop(depart_time, depart_city, depart_station), 
                            Stop(arrive_time, arrive_city, arrive_station), duration, cost))
    return results

codefile = open('codes.txt', 'r')
city_codes = {}
city_names = {}
for line in codefile:
    value, name = line.split(' ', 1)
    city_codes[int(value)] = name.strip()
    city_names[name.strip()] = int(value)
    
pathfile = open('locations.txt', 'r')
paths = {}
for line in pathfile:
    source, destinations = line.strip().split(":", 1)
    paths[source] = destinations.split("|")
    
source = "Christiansburg, VA"
destination = "Minneapolis, MN"

from simpleai.search import SearchProblem
class TravelProblem(SearchProblem):
    def __init__(self, source, destination):
        SearchProblem.__init__(self, source)
        self.destination = destination
    def actions(self, state):
        if state in paths:
            return paths[state]
        else:
            return []

    def result(self, state, action):
        return action

    def is_goal(self, state):
        return state == self.destination
        
import simpleai
result = simpleai.search.traditional.iterative_limited_depth_first(TravelProblem("Newark, DE", "Orlando, FL"))
print result.path()

#for time in xrange(30):
#    date = "5/%d/2013" % (time,)
#    for s in search(source, destination, date):
#        print s.cost, s.departure.date, s.arrival.date

#for new_city in paths[source]:
#    if new_city in city_names:
#        for s in search(source, city_names[new_city], "5/24/2013"):
#            print s.arrival.city, s.cost
        