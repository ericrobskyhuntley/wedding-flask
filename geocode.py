from app import AT, META
from geocoder import opencage, mapbox

import os
from dotenv import load_dotenv
load_dotenv()

def geocode(address, creds={}):
    """
    geocodes a given row of a dataframe based on address field.
    uses opencage and mapbox APIs (keys set in .env)
    """
    if address is None or len(address) == 0:
        match_type = None
        lat = None
        lng = None
        gc = None
    else:
        oc = opencage(address, key=creds["opencage"])
        if oc.ok:
            match_type = oc.json['raw']['components']['_type']
            if oc.confidence >= 9 and match_type == 'building':
                lat = oc.geometry['coordinates'][1]
                lng = oc.geometry['coordinates'][0]
                gc = 'oc'
            else:
                mb = mapbox(address, key=creds["mapbox"])
                if mb.ok:
                    if 'accuracy' in mb.json['raw']['properties']:
                        match_type = mb.json['raw']['properties']['accuracy']
                    if (match_type == 'rooftop') or (match_type == 'parcel'):
                        lat = mb.geometry['coordinates'][1]
                        lng = mb.geometry['coordinates'][0]
                        gc = 'mb'
                    else:
                        lat = oc.geometry['coordinates'][1]
                        lng = oc.geometry['coordinates'][0]
                        gc = 'oc'
                else:
                    lat = oc.geometry['coordinates'][1]
                    lng = oc.geometry['coordinates'][0]
                    gc = 'oc'
        else:
            mb = mapbox(address, key=creds["mapbox"])
            if mb.ok:
                lat = mb.geometry['coordinates'][1]
                lng = mb.geometry['coordinates'][0]
                gc = 'mb'
                if 'accuracy' in mb.json['raw']['properties']:
                    match_type = mb.json['raw']['properties']['accuracy']
                else:
                    match_type = 'mb_other'
            else:
                match_type = None
                lat = None
                lng = None
                gc = None
    return {
        "lat": lat,
        "lng": lng
    }


def address_if_blank(existing, new_col, new_dict, concat_string = ", "):
    """
    concatenates values of a dict based on whether value exists.
    """
    if new_col in new_dict:
        if len(existing) > 0:
            existing = existing + concat_string + new_dict[new_col]
        else:
            existing = new_dict[new_col]
    return existing

def process_and_geocode(table, creds = None):
    """
    Processes address and updates Airtable with geocoded coordinates.
    """
    if creds is None:
        try:
            creds = {
                "opencage": os.getenv("OPENCAGE_KEY"),
                "mapbox": os.getenv("MAPBOX_KEY")
            }
        except:
            print("No geocoding API credentials provided.")
            exit()
    at_entities = AT[table].all()
    for e in at_entities:
        e_f = e['fields']
        add = ""
        add = address_if_blank(add, "Address", e_f)
        add = address_if_blank(add, "City", e_f)
        add = address_if_blank(add, "State", e_f)
        add = address_if_blank(add, "Postal", e_f, concat_string = " ")
        add = address_if_blank(add, "Country", e_f)
        if len(add) > 0:
            print(f'Geocoding {add}')
            gc = geocode(add, creds = creds)
            AT[table].update(e["id"], {
                            "Lat": gc["lat"],
                            "Lng": gc["lng"]
                            })

if __name__ == "__main__":
    print("Processing and geocoding invited parties.")
    process_and_geocode("parties")
    print("Processing and geocoding vendors.")
    process_and_geocode("vendors")