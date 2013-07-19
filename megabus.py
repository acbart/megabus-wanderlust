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
        
    def __hash__(self):
        return hash((self.date.date(), self.city))
        
class Trip(object):
    def __init__(self, departure, arrival, duration, cost):
        self.departure = departure
        self.arrival = arrival
        self.duration = duration
        self.cost = cost
        
    def copy(self):
        return Trip(self.departure, self.arrival, self.duration, self.cost, self.origin, self.destination)
        
    def __str__(self):
        return str(vars(self))
        
    def __hash__(self):
        return hash( (hash(self.departure), hash(self.arrival)) )
        
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

# Get location codes
codefile = open('codes.txt', 'r')
city_codes = {}
city_names = {}
for line in codefile:
    value, name = line.split(' ', 1)
    city_codes[int(value)] = name.strip()
    city_names[name.strip()] = int(value)
    
# Get paths
pathfile = open('locations.txt', 'r')
paths = {}
for line in pathfile:
    source, destinations = line.strip().split(":", 1)
    paths[source] = destinations.split("|")

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
    if td.seconds//86400 == 0:
        if td.seconds//3600 == 0:
            return "%d minutes" % ((td.seconds//60)%60,)
        else:
            return "%d:%02d hours" % (td.seconds//3600, (td.seconds//60)%60)
    else:
        return "%d days, %d:%02d hours" % (td.seconds//86400, td.seconds//3600, (td.seconds//60)%60)
        
def day_range(start, end, **intervals):
    if start.date() <= end.date():
        while start.date() < end.date():
            yield start
            start = start + datetime.timedelta(**intervals)
        yield end
        
no_waiting = False
def long_trip(name, locations, dates):
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
    treks = [[Trip(Stop(date, origin, None),
                   Stop(date, origin, None),
                   0, "$0")] 
                for date in day_range(dates[0], dates[1], days=1)]
    finished_treks = []
    while treks:
        # A Trek is a list of Trips
        current_trek = treks.pop()
        destination = current_trek[-1].arrival
        current_city, current_date = destination.city, destination.date
        next_city = path[current_city]
        # Lookup the information about that date/city if we don't already have it
        if destination not in all_trips:
            all_trips[destination] = []
            for trip in search(city_names[current_city], city_names[next_city], 
                               current_date.strftime("%m/%d/%Y")):
                trip.origin = current_city
                trip.destination = next_city
                all_trips[destination].append(trip)
            # Also add all the trips if we assume we took them the next day
            for trip in search(city_names[current_city], city_names[next_city], 
                              (current_date+datetime.timedelta(days=1)).strftime("%m/%d/%Y")):
                trip.origin = current_city
                trip.destination = next_city
                all_trips[destination].append(trip)
        # Add the possible trips to this trek
        for next_trip in all_trips[destination]:
            # Don't add trips that are impossible (departs before arrival)
            if (current_date < next_trip.departure.date):
                # Don't add trips where you wait for more than 6 hours somewhere)
                if not no_waiting or (next_trip.departure.date - current_date < datetime.timedelta(hours=6)):
                    # if this is the final city, we move to the finished_treks
                    if next_city == locations[-1]:
                        finished_treks.append(current_trek + [next_trip])
                    else:
                        treks.append(current_trek + [next_trip])
                        
    with open(name+".txt", "w") as file:
        for id, trek in enumerate(finished_treks):
            previous_arrival = None
            waiting_hours = datetime.timedelta(days=0)
            all_hours_waiting = []
            for trip in trek[1:]:
                if previous_arrival != None:
                    waiting_hours = waiting_hours + trip.departure.date - previous_arrival
                    all_hours_waiting.append(trip.departure.date - previous_arrival)
                previous_arrival = trip.arrival.date
            if all(waiting_time < datetime.timedelta(hours=6) for waiting_time in all_hours_waiting):
                file.write("Trek: {}\n".format(id))
                file.write("\tTotal Cost: ${}\n".format(sum(map(float, [trip.cost[1:] for trip in trek]))))
                file.write("\tTotal Time: {}\n".format(days_hours_minutes(trek[-1].arrival.date - trek[1].departure.date)))
                file.write("\tTotal Time Waiting: {}\n".format(days_hours_minutes(waiting_hours)))
                file.write("\tLeave: {}\n".format(trek[1].departure.date.strftime("%a %b %d %I:%M %p")))
                file.write("\tArrive: {}\n".format(trek[-1].arrival.date.strftime("%a %b %d %I:%M %p")))
                file.write("\tItinerary:\n")
                previous_arrival = None
                for trip in trek[1:]:
                    if previous_arrival != None:
                        file.write("\t\tWait in {}: {}\n".format(trip.departure.city, days_hours_minutes(trip.departure.date - previous_arrival)))
                    file.write("\t\tLeave from {}: {}\n".format(trip.departure.city, trip.departure.date.strftime("%a %I:%M %p")))
                    file.write("\t\tArrive at {}: {}\n".format(trip.arrival.city, trip.arrival.date.strftime("%a %I:%M %p")))
                    previous_arrival = trip.arrival.date
    
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

NEWARK = "Newark, DE"
DC = "Washington, DC"
BLACKSBURG = "Christiansburg, VA"
ROUTE = ["Newark, DE", "Washington, DC", "Christiansburg, VA"]
if False:
    long_trip("Newark-VA", ROUTE, (20, 29))
    long_trip("VA-Newark", list(reversed(ROUTE)), (22, 29))

#ROUTE = ["Washington, DC", "Pittsburgh, PA", "Toledo, OH", "Chicago, IL", "Minneapolis, MN"]
long_trip("Newark to Christiansburg", ROUTE, ("8/18/2013", "8/21/2013"))
long_trip("Christiansburg to Newark", list(reversed(ROUTE)), ("8/24/2013", "8/26/2013"))
        
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
        
    