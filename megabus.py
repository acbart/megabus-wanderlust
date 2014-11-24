import requests
import time
from requests import ConnectionError
from bs4 import BeautifulSoup
import datetime
import itertools
from heapq import heappop, heappush
from util import to_ascii, load_json, safe_str

DATA = load_json("data/location_data.json")

class Trek(object):
    def __init__(self, start, trips=None):
        if trips is None:
            self.trips = []
        else:
            self.trips = list(trips)
        self.start = start
    
    @property
    def waiting_time(self):
        previous_arrival = self.trips[0].departure.date
        waiting_hours = datetime.timedelta(days=0)
        for trip in self.trips:
            waiting_hours += trip.departure.date - previous_arrival
            previous_arrival = trip.arrival.date
        return waiting_hours.seconds
        
    @property
    def value(self):
        if len(self.trips) > 1:
            return self.cost / float(1 + self.waiting_time//3600)
        else:
            return self.cost
    
    @property
    def cost(self):
        return sum(trip.cost for trip in self.trips)
        
    @property
    def arrival(self):
        if self.trips:
            return self.trips[-1].arrival
        else:
            return self.start
            
    @property
    def departure(self):
        return self.start
            
    def __getitem__(self, key):
        return self.trips[key]
        
    def __len__(self):
        return len(self.trips)
        
    def route(self):
        return [self.start] + [trip.arrival for trip in self.trips]
    
    def add_trip(self, trip):
        return Trek(self.start, self.trips + [trip])
        
    def __nonzero__(self):
        return bool(self.trips)

class Stop(object):
    def __init__(self, date, city, station=""):
        self.date = date
        self.city = city
        self.station = station
        
    def __str__(self):
        return "{} at {}".format(self.city, self.date.strftime("%m/%d/%Y"))
    
    def __repr__(self):
        return "{} at {}".format(self.city, self.date.strftime("%m/%d/%Y"))
        
    def __hash__(self):
        return hash((self.date.date(), self.city))
        
class Trip(object):
    def __init__(self, departure, arrival, duration, cost, url=""):
        self.departure = departure
        self.arrival = arrival
        self.duration = duration
        self.cost = cost
        if type(cost) in (str, unicode):
            self.cost = float(cost[1:])
        if url=="":
            url = (0, "")
        self.url = url
        
    def copy(self):
        return Trip(self.departure, self.arrival, self.duration, self.cost, self.origin, self.destination, self.url)
        
    def __str__(self):
        return str(vars(self))
        
    def __hash__(self):
        return hash( (hash(self.departure), hash(self.arrival)) )
    
HOURS = [datetime.time(hour=10, minute=30), datetime.time(hour=11, minute=25),
         datetime.time(hour=12, minute=30), datetime.time(hour=13, minute=25),
         datetime.time(hour=14, minute=15), datetime.time(hour=16, minute=25),
         datetime.time(hour=18, minute=15), datetime.time(hour=20, minute=15),
         datetime.time(hour=22, minute=25)]

SEARCH_CACHE = {}
def cache_search(origin, destination, date):
    if type(date) != str:
        string_date = date.strftime("%m/%d/%Y")
    if type(origin) in (str, unicode):
        origin = city_names[origin.replace(" , ", ", ")]
    if type(destination) in (str, unicode):
        destination = city_names[destination.replace(" , ", ", ")]
    if origin == 999:
        return_times = [[datetime.datetime.combine(new_date, time) for time in HOURS] for new_date in days_ahead_range(date, 4)]
        return [Trip(Stop(new_date, city_codes[origin]),
                     Stop(new_date, city_codes[destination]), 
                     "2hrs 25mins", 
                     "$0.00") 
                 for new_date in itertools.chain(*return_times)]
    elif origin == 118 and destination == 102:
        LEAVE1 = datetime.datetime.combine(date, datetime.time(hour=4, minute=10))
        ARRIVE1 = datetime.datetime.combine(date, datetime.time(hour=9, minute=5))
        LEAVE2 = datetime.datetime.combine(date, datetime.time(hour=17, minute=10))
        ARRIVE2 = datetime.datetime.combine(date, datetime.time(hour=22, minute=5))
        return [Trip(Stop(LEAVE1, city_codes[origin]),
                     Stop(ARRIVE1, city_codes[destination]), 
                     "4hrs 55mins", 
                     "$36.00"),
                Trip(Stop(LEAVE2, city_codes[origin]),
                     Stop(ARRIVE2, city_codes[destination]), 
                     "4hrs 55mins", 
                     "$36.00")]
    elif (origin, destination, string_date) in SEARCH_CACHE:
        return SEARCH_CACHE[(origin, destination, string_date)]
    else:
        return search(origin, destination, string_date)
        
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
    complete_url = result.url
    result = to_ascii(result.content).encode('ascii', 'ignore')
    result = BeautifulSoup(result)
    results = []
    for id, r in enumerate(result.find_all(class_ = "journey standard")):
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
                            Stop(arrive_time, arrive_city, arrive_station), duration, cost, url=(id+1, complete_url)))
    return results

# Get location codes
city_codes = DATA['code_to_city']
city_names = DATA['city_to_code']
    
# Get paths
paths = DATA['destination_map']

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
    
    def cost(self, start, action, end):
        if end in city_names:
            paths = search(city_names[start], city_names[end], "5/23/2013")
        else:
            return 1000
        if not paths:
            return 1000
        else:
            return min([float(path.cost.replace("$","")) for path in paths]) 

    def result(self, state, action):
        return action

    def is_goal(self, state):
        return state == self.destination
        
def days_hours_minutes(td):
    if td.days == 0:
        if td.seconds//3600 == 0:
            return "%d minutes" % ((td.seconds//60)%60,)
        else:
            return "%d:%02d hours" % (td.seconds//3600, (td.seconds//60)%60)
    else:
        return "%d days, %d:%02d hours" % (td.days, td.seconds//3600, (td.seconds//60)%60)
        
def day_range(start, end, **intervals):
    if start.date() <= end.date():
        while start.date() < end.date():
            yield start
            start = start + datetime.timedelta(**intervals)
        yield end
        
def days_ahead_range(start, plus):
    for x in xrange(plus+1):
        yield start + datetime.timedelta(days=x)
        
no_waiting = False
MAX_HOURS_WAITING = 24
def long_trip(name, locations, dates):
    filename = "{}.txt".format(name)
    file = open(filename, 'w')
    if type(dates[0]) == str:
        dates = map(lambda x : datetime.datetime.strptime(x, "%m/%d/%Y"), dates)
    all_trips = {}
    origin = locations[0]
    
    # Make the lookup table for travelling between destinations
    path = {}
    for destination in locations[1:]:
        path[origin] = destination
        origin = destination
    
    origin = locations[0]
    treks = list(reversed([(0, Trek(Stop(date, origin, None)))
                for date in day_range(dates[0], dates[1], days=1)]))
    finished_treks = []
    while treks:
        try:
            # A Trek is a list of Trips
            cost, current_trek = heappop(treks)
            print current_trek.route()
            destination = current_trek.arrival
            current_city, current_date = destination.city, destination.date
            next_city = path[current_city]
            # Look up the possible trips
            results = cache_search(current_city, next_city, current_date)
            results += cache_search(current_city, next_city, current_date+datetime.timedelta(days=1))
            # Add the possible trips to this trek
            for next_trip in results:
                # Don't add trips that are impossible (departs before arrival)
                if (current_date < next_trip.departure.date):
                    # Don't add trips where you wait for more than 6 hours somewhere)
                    if not no_waiting or (next_trip.departure.date - current_date < datetime.timedelta(hours=6)):
                        # if this is the final city, we move to the finished_treks
                        if next_city == locations[-1]:
                            
                            #finished_treks.append(current_trek + [next_trip])
                            report_append(file, len(finished_treks), current_trek.add_trip(next_trip))
                        else:
                            new = current_trek.add_trip(next_trip)
                            heappush(treks, (-len(new), new))
                            #treks.append(current_trek.add_trip(next_trip))
        except ConnectionError, c:
            print "Time out, try again"
            heappush(treks, (cost, current_trek))
            time.sleep(1)
    file.close()
        #report(name, finished_treks)
        
def report_append(file, id, trek):
    previous_arrival = trek[0].departure.date
    waiting_hours = datetime.timedelta(days=0)
    all_hours_waiting = []
    for trip in trek:
        waiting_hours += trip.departure.date - previous_arrival
        all_hours_waiting.append(trip.departure.date - previous_arrival)
        previous_arrival = trip.arrival.date
    file.write("Trek: {} -> {} for ${} over {}\n".format(trek[0].departure.date.strftime("%a %b %d %I:%M %p"), trek.arrival.date.strftime("%a %b %d %I:%M %p"), trek.cost, days_hours_minutes(trek.arrival.date - trek[0].departure.date)))
    file.write("\tTotal Cost: ${}\n".format(trek.cost))
    file.write("\tTotal Time: {}\n".format(days_hours_minutes(trek.arrival.date - trek[0].departure.date)))
    file.write("\tTotal Time Waiting: {}\n".format(days_hours_minutes(waiting_hours)))
    file.write("\tLeave: {}\n".format(trek[0].departure.date.strftime("%a %b %d %I:%M %p")))
    file.write("\tArrive: {}\n".format(trek.arrival.date.strftime("%a %b %d %I:%M %p")))
    file.write("\tItinerary:\n")
    file.write("\t{}\n".format(" -> ".join([stop.city for stop in trek.route()])))
    previous_arrival = trek[0].departure.date
    tickets = []
    for trip in trek:
        if previous_arrival != trek[0].departure.date:
            file.write("\t\tWait in {}: {}\n".format(trip.departure.city, days_hours_minutes(trip.departure.date - previous_arrival)))
        file.write("\t\tLeave from {}: {}\n".format(trip.departure.city, trip.departure.date.strftime("%a %I:%M %p")))
        file.write("\t\tArrive at {}: {}\n".format(trip.arrival.city, trip.arrival.date.strftime("%a %I:%M %p")))
        tickets.append(trip.url)
        previous_arrival = trip.arrival.date
    file.write("\tTicket URLs:\n")
    for id_on_page, ticket in tickets:
        file.write("\t\tTicket URL (#{}): {}\n\n".format(id_on_page, ticket))
    file.flush()
    
def report(name, treks, max_hours_waiting=None):
    with open(name+".txt", "w") as file:
        for id, trek in enumerate(treks):
            previous_arrival = trek[0].departure.date
            waiting_hours = datetime.timedelta(days=0)
            all_hours_waiting = []
            for trip in trek:
                waiting_hours += trip.departure.date - previous_arrival
                all_hours_waiting.append(trip.departure.date - previous_arrival)
                previous_arrival = trip.arrival.date
            if max_hours_waiting is None or all(waiting_time < datetime.timedelta(hours=max_hours_waiting) for waiting_time in all_hours_waiting):
                file.write("Trek: {}\n".format(id))
                file.write("\tTotal Cost: ${}\n".format(trek.cost))
                file.write("\tTotal Time: {}\n".format(days_hours_minutes(trek.arrival.date - trek[0].departure.date)))
                file.write("\tTotal Time Waiting: {}\n".format(days_hours_minutes(waiting_hours)))
                file.write("\tLeave: {}\n".format(trek[0].departure.date.strftime("%a %b %d %I:%M %p")))
                file.write("\tArrive: {}\n".format(trek.arrival.date.strftime("%a %b %d %I:%M %p")))
                file.write("\tItinerary:\n")
                file.write("\t{}\n".format(" -> ".join([stop.city for stop in trek.route()])))
                previous_arrival = trek[0].departure.date
                tickets = []
                for trip in trek:
                    if previous_arrival != trek[0].departure.date:
                        file.write("\t\tWait in {}: {}\n".format(trip.departure.city, days_hours_minutes(trip.departure.date - previous_arrival)))
                    file.write("\t\tLeave from {}: {}\n".format(trip.departure.city, trip.departure.date.strftime("%a %I:%M %p")))
                    file.write("\t\tArrive at {}: {}\n".format(trip.arrival.city, trip.arrival.date.strftime("%a %I:%M %p")))
                    tickets.append(trip.url)
                    previous_arrival = trip.arrival.date
                file.write("\tTicket URLs:\n")
                for id_on_page, ticket in tickets:
                    file.write("\t\tTicket URL (#{}): {}\n".format(id_on_page, ticket))
    
    #first = city_names[locations[0]]
    #second = city_names[locations[1]]
    #third = city_names[locations[2]]
    #trip_file.write("{} to {}\n".format(locations[0], locations[2]))
    #for date in date_range:
        #trip_file.write("\t%s\n" % date.strftime("%m/%d/%Y"))
        #for first_trip in search(first, second, date.strftime("%m/%d/%Y")):
            #for second_trip in search(second, third, date.strftime("%m/%d/%Y")) + search(second, third, (date + datetime.timedelta(days=1)).strftime("%m/%d/%Y")):
                #if first_trip.arrival.date < second_trip.departure.date and (second_trip.departure.date - first_trip.arrival.date < datetime.timedelta(hours=6)):
                    #trip_file.write("\t\tCost: $" + str(float(first_trip.cost[1:]) + float(second_trip.cost[1:])) + "\n")
                    #trip_file.write("\t\tTotal Hours: " + days_hours_minutes(second_trip.arrival.date - first_trip.departure.date) + "\n")
                    #trip_file.write("\t\tLeave 1st: " + first_trip.departure.date.strftime("%a %I:%M %p") + "\n")
                    #trip_file.write("\t\tArrive 2nd: " + first_trip.arrival.date.strftime("%a %I:%M %p") + "\n")
                    #trip_file.write("\t\tWait: " + days_hours_minutes(second_trip.departure.date - first_trip.arrival.date) + "\n")
                    #trip_file.write("\t\tLeave 2nd: " + second_trip.departure.date.strftime("%a %I:%M %p") + "\n")
                    #trip_file.write("\t\tArrive 3rd: " + second_trip.arrival.date.strftime("%a %I:%M %p") + "\n")
                    #trip_file.write("\n")
       # print "\t\t", trip.cost, trip.departure.date.time(), "->", trip.arrival.date.time()
       # print "\t\t", trip.cost, trip.departure.date.time(), "->", trip.arrival.date.time()
        
#print long_trip(["Newark, DE", "Washington, DC", "Christiansburg, VA"], (17, 28))

if __name__ == "__main__":
    NEWARK = "Baltimore, MD"
    DC = "Washington, DC"
    BLACKSBURG = "Christiansburg, VA"
    ROUTE = ["Baltimore, MD", "Washington, DC", "Christiansburg, VA"]
    if False:
        long_trip("Newark-VA", ROUTE, (20, 25))
        long_trip("VA-Newark", list(reversed(ROUTE)), (22, 27))

    #ROUTE = ["Washington, DC", "Pittsburgh, PA", "Toledo, OH", "Chicago, IL", "Minneapolis, MN"]    
    long_trip("BaltimoreToBlacksburg", list(ROUTE), ("10/13/2013", "10/13/2013"))
    long_trip("BlacksburgToBaltimore", list(reversed(ROUTE)), ("10/11/2013", "10/12/2013"))
    #long_trip("Newark to Christiansburg", ROUTE, ("8/12/2013", "8/15/2013"))
        
#import simpleai
#result = simpleai.search.traditional.uniform_cost(TravelProblem("Newark, DE", "Orlando, FL"))
#print result.path()

#for time in xrange(30):
#    date = "5/%d/2013" % (time,)
#    for s in search(source, destination, date):
#        print s.cost, s.departure.date, s.arrival.date

#for new_city in paths[source]:
#    if new_city in city_names:
#        for s in search(source, city_names[new_city], "5/24/2013"):
#            print s.arrival.city, s.cost
        
    