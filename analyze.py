import sys
import networkx as nx
import matplotlib.pyplot as plt
import json
from megabus import cache_search, Trek, Stop, Trip, report, day_range, report_append, long_trip
import datetime
from heapq import heappop, heappush
from random import randint
import time
from requests import ConnectionError

def rand():
    return randint(1, 100)

G=nx.Graph()

file = open("calculated_edges.txt", "r")
data = json.load(file)
file.close()

for pair in data:
    G.add_edge(pair["origin"], pair["destination"], weight=pair["duration"])
        
ROUTE = nx.dijkstra_path(G,source="Christiansburg, VA",target="Atlanta, GA")
ROUTE = [str(r) for r in ROUTE]

print ROUTE
long_trip("ChristiansburgToIndianpolis", ROUTE, ("10/20/2013", "10/27/2013"))

sys.exit()

def wander(start_date, end_date, start_city, no_loop_back=True, money_limit = None):
    filename = "{} _ {}.txt".format(start_city.replace(",",""), start_date.replace("/","-"))
    if type(start_date) == str:
        start_date, end_date = map(lambda x : datetime.datetime.strptime(x, "%m/%d/%Y"), (start_date, end_date))
    incomplete_routes = [(0, Trek(Stop(start_date, start_city)))]
    #finished_routes = []
    id = 0
    file = open(filename, 'w')
    while incomplete_routes:
        try:
            cost, trek = heappop(incomplete_routes)
            print "Trying", trek.route(), cost
            next_stops = G[trek.arrival.city]
            next_trips = []
            for stop, distance in next_stops.iteritems():
                for date in day_range(trek.arrival.date, end_date, days=1):
                    next_trips.extend(cache_search(trek.arrival.city,
                                                   stop,
                                                   date))
            if trek.arrival.city == start_city and trek:
                report_append(file, id, trek)
                id+= 1
            for trip in next_trips:
                if trip.arrival.date <= end_date and trek.arrival.date < trip.departure.date:
                    if trek.arrival.city != trip.arrival.city:
                        new_trek = trek.add_trip(trip)
                        if money_limit is None or new_trek.cost <= money_limit:
                            if not no_loop_back or (trek.departure.city not in [stop.city for stop in new_trek.route()[1:-1]]):
                                if trip.arrival.city == start_city:
                                    #print "Found", new_trek.route()
                                    report_append(file, id, new_trek)
                                    id+= 1
                                heappush(incomplete_routes, (new_trek.value, new_trek))
        except ConnectionError, c:
            print c
            heappush(incomplete_routes, (new_trek.value, trek))
            time.sleep(1)

    #finished_routes.sort(key=lambda trek: trek.cost / float(len(trek)))
    file.close()
    #report("test", finished_routes)
    #return finished_routes
# Given a starting point
# Find all paths possible from that point
# Wish to minimize cost
# Wish to Maximize distance
# Limit travel to certain time range
# Must end where you started
print wander("10/4/2013", "10/6/2013", "Christiansburg, VA", money_limit=30)
 
#print nx.bfs_successors(G, "Newark, DE")
 
#from megabus import long_trip
#long_trip("test_route.txt", ROUTE, ("8/5/2013", "8/7/2013"))

#pos=nx.spring_layout(G)
        
#nx.draw_networkx_labels(G,pos,font_size=12,font_family='sans-serif')
#nx.draw_networkx_nodes(G,pos,node_size=700)
#nx.draw_networkx_edges(G,pos,width=6)
        
#plt.axis('off')
#plt.savefig("us-map.png")
#plt.show()