from datetime import datetime
from zoneinfo import ZoneInfo
from flask_mail import Mail, Message
from flask import render_template
from markdown import markdown
from slugify import slugify
from operator import itemgetter
from icalendar import Calendar, Event
import base64
from pyairtable.formulas import Field, FIND, OR, EQ
from itertools import groupby
from functools import partial
import os

def get_airtable():
    from pyairtable import Api
    api = Api(os.getenv("AT_KEY"))

    return {
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


def get_meta():
    AT = get_airtable()
    meta = AT["meta"].first(
        fields=[
            "Published",
            "Times",
            "Names",
            "Cities",
            "Registry",
            "States",
            "SiteURL",
        ]
    )["fields"]
    meta["CityStates"] = unique(
        [c + ", " + s for c, s in zip(meta["Cities"], meta["States"])]
    )
    meta["UniqueDates"] = unique([dt_parse(dt).date() for dt in meta["Times"]])
    meta["ShortNames"] = [n.split()[0] for n in meta["Names"]]
    meta["ThingsToDo"] = AT["thingsToDo"].all()

    for key in ["Cities", "States", "Times"]:
        del meta[key]

    meta["Path"] = "/"

    if "Published" not in meta:
        meta["Published"] = False
    return meta


def email_confirm(app, yes, no, recipients):
    mail = Mail(app)

    META = get_meta()

    rsvp = Message(
        f"{' & '.join(META['ShortNames'])} | Thanks for your RSVP!",
        sender=os.getenv("MAIL_USERNAME"),
        cc=[os.getenv("MAIL_USERNAME")],
        recipients=recipients,
    )

    _ = partial(render_template, yes=yes, no=no, meta=META)

    rsvp.html = _("rsvp_conf.html")
    mail.send(rsvp)
    return


def dt_parse(string):
    return datetime.fromisoformat(string.replace("Z", "+00:00")).astimezone(
        ZoneInfo("America/New_York")
    )


def unique(l):
    return list(set(l))


def address_if_blank(existing, new_col, new_dict, concat_string=", "):
    """
    concatenates values of a dict based on whether value exists.
    """
    if new_col in new_dict:
        if len(existing) > 0:
            existing = existing + concat_string + new_dict[new_col]
        else:
            existing = new_dict[new_col]
    return existing


def normalize_event(raw):
    f = raw["fields"]

    def first(x):
        return x[0] if isinstance(x, list) else x

    return {
        "Name": f.get("Name"),
        "StartTime": f.get("StartTime"),
        "EndTime": f.get("EndTime"),
        "Description": f.get("Description"),
        "VenueName": first(f.get("VenueName")),
        "VenueAddress": first(f.get("VenueAddress")),
        "VenueCity": first(f.get("VenueCity")),
        "VenueState": first(f.get("VenueState")),
        "VenuePostal": first(f.get("VenuePostal")),
        "VenueURL": first(f.get("VenueURL")) if f.get("VenueURL") else None,
        "Lat": first(f.get("Lat")),
        "Lng": first(f.get("Lng")),
        "Artists": f.get("Artists"),
    }


def enrich_event(e):
    location = (
        f"{e['VenueAddress']}, "
        f"{e['VenueCity']}, "
        f"{e['VenueState']} {e['VenuePostal']}"
    )

    return {
        **e,
        "StartTime": dt_parse(e["StartTime"]),
        "EndTime": dt_parse(e["EndTime"]),
        "Slug": slugify(e["Name"]),
        "Location": location,
        "Directions": f"https://www.google.com/maps?saddr=My+Location&daddr={location}",
        "Description": markdown(e["Description"]) if e.get("Description") else None,
    }


def build_ics(e):
    META = get_meta()
    cal = Calendar()
    names = " & ".join(META["ShortNames"])
    cal.add("prodid", f"-//{names} Wedding//Event Generator//EN")
    cal.add("version", "2.0")

    event = Event()
    event.add("summary", names + ": " + e["Name"])
    event.add("dtstart", e["StartTime"])
    event.add("dtend", e["EndTime"])
    event.add("location", e["Location"])

    if e.get("Description"):
        event.add("description", e["Description"])

    if META.get("URL"):
        event.add("url", META["URL"])

    event.add("geo", (float(e["Lat"]), float(e["Lng"])))

    cal.add_component(event)

    return base64.b64encode(cal.to_ical()).decode("utf-8")


def process_artists(e):
    AT = get_airtable()
    if not e.get("Artists"):
        return e

    artists = []
    for artist in e["Artists"]:
        a = AT["vendors"].get(artist)["fields"]
        if a.get("Status") == "Confirmed":
            artists.append(
                {
                    "Website": a.get("Website"),
                    "Name": a.get("Name"),
                    "Role": a.get("Role"),
                }
            )

    artists = sorted(artists, key=itemgetter("Role"))

    grouped = {}
    for role, group in groupby(artists, key=itemgetter("Role")):
        grouped[role] = list(group)

    return {**e, "Artists": grouped}


def process_events(events):
    processed = []

    for raw in events:
        e = normalize_event(raw)
        e = enrich_event(e)
        e = process_artists(e)
        e["ics"] = build_ics(e)

        processed.append(e)

    return groupby(processed, lambda x: x["StartTime"].date())


def compose_formula(list, field):
    f = []
    for term in list:
        f.append(str(FIND(term, "ARRAYJOIN(" + str(Field(field)) + ")")))
    f.append(str(EQ(0, Field(field))))
    return OR(",".join(f))


def check_none(field, values, values_dict, none_val=None):
    field_lc = field.lower()
    field_id = "_".join([field_lc, "id"])
    values_dict[field_id] = "_".join([field_lc, values_dict["id"]])
    if field not in values:
        values_dict[field] = none_val
    else:
        values_dict[field] = values[field]
    return values_dict


def check_form_list(field, values, request):
    field_lc = field.lower()
    field_id = "_".join([field_lc, "id"])
    if field_id in values:
        if values[field_id] in request.form:
            values[field] = request.form.getlist(values[field_id])
        else:
            values[field] = []
    return values


def check_form(field, values, request):
    field_lc = field.lower()
    field_id = "_".join([field_lc, "id"])
    if field_id in values:
        if values[field_id] in request.form:
            if request.form[values[field_id]] == "None":
                values[field] = None
            else:
                values[field] = request.form[values[field_id]]
    return values


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
        from geocoder import opencage, mapbox

        oc = opencage(address, key=creds["opencage"])
        if oc.ok:
            match_type = oc.json["raw"]["components"]["_type"]
            if oc.confidence >= 9 and match_type == "building":
                lat = oc.geometry["coordinates"][1]
                lng = oc.geometry["coordinates"][0]
                gc = "oc"
            else:
                mb = mapbox(address, key=creds["mapbox"])
                if mb.ok:
                    if "accuracy" in mb.json["raw"]["properties"]:
                        match_type = mb.json["raw"]["properties"]["accuracy"]
                    if (match_type == "rooftop") or (match_type == "parcel"):
                        lat = mb.geometry["coordinates"][1]
                        lng = mb.geometry["coordinates"][0]
                        gc = "mb"
                    else:
                        lat = oc.geometry["coordinates"][1]
                        lng = oc.geometry["coordinates"][0]
                        gc = "oc"
                else:
                    lat = oc.geometry["coordinates"][1]
                    lng = oc.geometry["coordinates"][0]
                    gc = "oc"
        else:
            mb = mapbox(address, key=creds["mapbox"])
            if mb.ok:
                lat = mb.geometry["coordinates"][1]
                lng = mb.geometry["coordinates"][0]
                gc = "mb"
                if "accuracy" in mb.json["raw"]["properties"]:
                    match_type = mb.json["raw"]["properties"]["accuracy"]
                else:
                    match_type = "mb_other"
            else:
                match_type = None
                lat = None
                lng = None
                gc = None
    return {"lat": lat, "lng": lng}


def process_and_geocode(table, creds=None):
    """
    Processes address and updates Airtable with geocoded coordinates.
    """
    AT = get_airtable()
    if creds is None:
        try:
            creds = {
                "opencage": os.getenv("OPENCAGE_KEY"),
                "mapbox": os.getenv("MAPBOX_KEY"),
            }
        except:
            print("No geocoding API credentials provided.")
            exit()
    at_entities = AT[table].all()
    for e in at_entities:
        e_f = e["fields"]
        add = ""
        add = address_if_blank(add, "Address", e_f)
        add = address_if_blank(add, "City", e_f)
        add = address_if_blank(add, "State", e_f)
        add = address_if_blank(add, "Postal", e_f, concat_string=" ")
        add = address_if_blank(add, "Country", e_f)
        if len(add) > 0:
            print(f"Geocoding {add}")
            gc = geocode(add, creds=creds)
            AT[table].update(e["id"], {"Lat": gc["lat"], "Lng": gc["lng"]})