from pyairtable import Api
import os
from .helpers import dt_parse, unique

api = Api(os.getenv("AT_KEY"))

AT = {
    "venues": api.table(os.getenv("AT_BASE_ID"), "Venues"),
    "events": api.table(os.getenv("AT_BASE_ID"), "Events"),
    "people": api.table(os.getenv("AT_BASE_ID"), "People"),
    "parties": api.table(os.getenv("AT_BASE_ID"), "Parties"),
    "qa": api.table(os.getenv("AT_BASE_ID"), "QA"),
    "meta": api.table(os.getenv("AT_BASE_ID"), "Meta"),
    "vendors": api.table(os.getenv("AT_BASE_ID"), "Vendors"),
    "accommodations": api.table(os.getenv("AT_BASE_ID"), "Accommodations"),
    "thingsToDo": api.table(os.getenv("AT_BASE_ID"), "ThingsToDo")
}

META = AT["meta"].first(
    fields = ['Published', 
              'Times', 
              'Names', 
              'Cities', 
              'Registry',
              'States',
              'SiteURL']
              )['fields']
META["CityStates"] = unique([c + ", " + s for c, s in zip(META["Cities"], META["States"])])
META['UniqueDates'] = unique([dt_parse(dt).date() for dt in META['Times']])
META['ShortNames'] = [n.split()[0] for n in META['Names']]
META['ThingsToDo'] = AT['thingsToDo'].all()

# Remove extraneous keys.
for key in ["Cities", "States", "Times"]:
    del META[key]
    
META['Path'] = '/'

if "Published" not in META:
    META["Published"] = False