import requests
import json
import time

pathfile = open('locations.txt', 'r')
edges = []
for line in pathfile:
    origin, destinations = line.strip().split(":", 1)
    for destination in destinations.split("|"):
        edges.append( (origin, destination))

weighted_edges = []
while edges:
    origin, destination = edges.pop()
    url = "http://maps.googleapis.com/maps/api/directions/json"
    data = {"origin" : origin,
            "destination" : destination,
            "sensor": "false"}
    result = requests.get(url, params=data).json()
    if result["status"] == "OK":
        edge = {}
        edge["distance"] = result["routes"][0]["legs"][0]["distance"]["value"]
        edge["duration"] = result["routes"][0]["legs"][0]["duration"]["value"]
        edge["end"] = result["routes"][0]["legs"][0]["end_address"]
        edge["start"] = result["routes"][0]["legs"][0]["start_address"]
        edge["origin"] = origin
        edge["destination"] = destination
        weighted_edges.append(edge)
        print "Finished", edge["start"], edge["end"], "({} -> {})".format(origin, destination)
    else:
        time.sleep(1)
        edges.append((origin, destination))
        print "Failed", "({} -> {})".format(origin, destination)
        
file = open("calculated_edges.txt", "w")
json.dump(weighted_edges, file)
file.close()