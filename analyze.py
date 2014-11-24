import sys, os
import networkx as nx
import matplotlib.pyplot as plt
from heapq import heappop, heappush
from random import randint
import time, datetime
from requests import ConnectionError

from megabus import Trek, Stop, Trip
from megabus import cache_search, report, day_range, report_append, long_trip
from util import load_json, safe_str

DATA = load_json("data/location_data.json")
america = nx.Graph()
for edge in DATA['weighted_destinations']:
    america.add_edge(edge["origin"], edge["destination"], 
                     weight=edge["duration"])

def find_route(source="Christiansburg, VA", target="Newark, DE",
               start= "12/20/2014", end = "12/27/2014"):
    route = nx.dijkstra_path(america,source,target)
    route = [str(r) for r in route]
    long_trip("{}-{}".format(source,target), route, (start, end))
    return route

find_route()
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