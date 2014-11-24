'''
Generates the city codes and destination mappings

author: acbart
'''
from __future__ import print_function
import requests
from bs4 import BeautifulSoup
import datetime
import os, sys
import json
import time
from util import to_ascii, csv_to_lod

MAIN_PAGE_URL = "http://us.megabus.com/"
GET_DESTINATIONS_URL = "http://us.megabus.com/support/journeyplanner.svc/GetDestinations?originId={}"
GOOGLE_MAPS_URL = "http://maps.googleapis.com/maps/api/directions/json"

DATA = {}

print("Getting the latest megabus city codes")
megabus_main_page = requests.get(MAIN_PAGE_URL).content
megabus_main_page_soup = BeautifulSoup(megabus_main_page)

options = megabus_main_page_soup.select("#JourneyPlanner_ddlOrigin option")
city_codes = [(o['value'], str(o.string))
                    for o in options if 'selected' not in o.attrs]
DATA['code_to_city'] = {o['value'] : str(o.string)
                        for o in options if 'selected' not in o.attrs}
DATA['city_to_code'] = {str(o.string): o['value']
                        for o in options if 'selected' not in o.attrs}

print("Getting the destinations for each city")
DATA['destination_map'] = {}
edges = []
for city_id, city_name in city_codes:
    destination_page = requests.get(GET_DESTINATIONS_URL.format(city_id)).json()
    DATA['destination_map'][city_name] = []
    for raw_city in destination_page['d']:
        destination_name = raw_city['descriptionField']
        destination_id = raw_city['idField']
        edges.append((city_name, destination_name))
        DATA['destination_map'][city_name].append(destination_name)
    print("\t", city_name, DATA['destination_map'][city_name])
    
print("Using Google Maps to calculate distance between cities")
DATA['weighted_destinations'] = []
while edges:
    origin, destination = edges.pop()
    data = {"origin" : origin,
            "destination" : destination,
            "sensor": "false"}
    result = requests.get(GOOGLE_MAPS_URL, params=data).json()
    if result["status"] == "OK":
        edge = {
            "distance": result["routes"][0]["legs"][0]["distance"]["value"],
            "duration": result["routes"][0]["legs"][0]["duration"]["value"],
            "end": result["routes"][0]["legs"][0]["end_address"],
            "start": result["routes"][0]["legs"][0]["start_address"],
            "origin": origin,
            "destination": destination
        }
        DATA['weighted_destinations'].append(edge)
        print("\tFinished", edge["start"], edge["end"], "({} -> {})".format(origin, destination))
        # Randomly slow it down a little
        if len(DATA['weighted_destinations']) % 10 == 0:
            time.sleep(1)
    else:
        time.sleep(1)
        edges.append((origin, destination))
        print("\tFailed", "({} -> {})".format(origin, destination))

print("Dumping to data/location_data.json")
json.dump(DATA, open("data/location_data.json", 'w'))