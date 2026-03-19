from flask import render_template, request, url_for, redirect, Blueprint, flash
from flask_login import current_user

from markdown import markdown
from slugify import slugify
from pyairtable.formulas import match, Field, FIND, OR, EQ
from itertools import groupby
from operator import itemgetter
from icalendar import Calendar, Event
from datetime import datetime
import base64

from .config import AT, META
from .helpers import dt_parse
from .app import app
from .utils import email_confirm

META["Path"] = None

wedding = Blueprint(
    "wedding", __name__, template_folder="templates", static_folder="static"
)


@wedding.route("/")
def home_redirect():
    return redirect(url_for("wedding.home"))


@wedding.route("/home")
def home():
    data = META
    META["Path"] = request.path
    data["LandingText"] = markdown(
        AT["meta"].first(fields=["LandingText"])["fields"]["LandingText"]
    )
    return render_template("home.html", data=data)

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
    cal = Calendar()
    names = " & ".join(META["ShortNames"])
    cal.add('prodid', f"-//{names} Wedding//Event Generator//EN")
    cal.add('version', '2.0')

    event = Event()
    event.add('summary', names + ": " + e["Name"])
    event.add('dtstart', e["StartTime"])
    event.add('dtend', e["EndTime"])
    event.add('location', e["Location"])

    if e.get("Description"):
        event.add('description', e["Description"])

    if META.get("URL"):
        event.add('url', META["URL"])

    event.add('geo', (float(e["Lat"]), float(e["Lng"])))

    cal.add_component(event)

    return base64.b64encode(
        cal.to_ical()
    ).decode("utf-8")
    
def process_artists(e):
    if not e.get("Artists"):
        return e

    artists = []
    for artist in e["Artists"]:
        a = AT["vendors"].get(artist)["fields"]
        if a.get("Status") == "Confirmed":
            artists.append({
                "Website": a.get("Website"),
                "Name": a.get("Name"),
                "Role": a.get("Role"),
            })

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


@wedding.route("/itinerary")
def itinerary():
    if META["Published"]:
        data = META
        META["Path"] = request.path
        if current_user.is_authenticated:
            person = AT["people"].get(current_user.id).get("fields")
            if "GroupNames" in person:
                formula = compose_formula(person["GroupNames"], "LimitedInviteNames")
            else:
                formula = EQ(0, Field("LimitedInviteNames"))
            events = AT["events"].all(formula=formula, sort=["StartTime"])

            itinerary = []
            for date, event in process_events(events):
                d = {}
                d["Date"] = date
                date_event_names = []

                venues = []
                for v, e in groupby(
                    event,
                    lambda x: {
                        "VenueName": x["VenueName"],
                        "VenueAddress": x["VenueAddress"],
                        "VenueCity": x["VenueCity"],
                        "VenueState": x["VenueState"],
                        "VenuePostal": x["VenuePostal"],
                        "VenueURL": x["VenueURL"],
                        "Lat": x["Lat"],
                        "Lng": x["Lng"],
                        "Directions": x["Directions"],
                    },
                ):
                    venue = v
                    es = []
                    for i in e:
                        if i.get("DressCode") == "Casual":
                            i["DressCodeDesc"] = (
                                "Wear whatever makes you feel comfortable! Jeans okay."
                            )
                        if i.get("DressCode") == "Feel-Good Festive":
                            i["DressCodeDesc"] = (
                                "Wear whatever puts you in the mood to celebrate. No jeans, no tuxes. Dancing shoes."
                            )
                        date_event_names.append(i["Name"])
                        d["DateDesc"] = " ◦ ".join(date_event_names)
                        es.append(i)
                    import re

                    venue["Slug"] = re.sub("[^0-9a-zA-Z]+", "_", v["VenueName"].lower())
                    venue["Events"] = es
                    venues.append(venue)
                d["Venues"] = venues
                itinerary.append(d)
            data["itinerary"] = itinerary
            return render_template("itinerary.html", data=data)
        else:
            return redirect(url_for("auth.login"))
    else:
        return redirect(url_for("wedding.home"))


@wedding.route("/qa")
def qa():
    if META["Published"]:
        data = META
        META["Path"] = request.path
        d = []
        for i in AT["qa"].all(formula=EQ(1, Field("Publish"))):
            i = i["fields"]
            i["Question"] = markdown(i["Question"])
            i["Answer"] = markdown(i["Answer"])
            d.append(i)
        data["qa"] = d
        return render_template("qa.html", data=data)
    else:
        return redirect(url_for("wedding.home"))


@wedding.route("/accommodations")
def accommodations():
    if META["Published"]:
        data = META
        META["Path"] = request.path
        acc = []
        for a in AT["accommodations"].all(formula=EQ(1, Field("Listed"))):
            a = a["fields"]
            a["Name"] = a["Name"][0]
            a["Slug"] = a["Name"].lower().replace(" ", "_").replace("'", "_")
            a["Website"] = a["Website"][0]
            a["Deadline"] = dt_parse(a["Deadline"])
            a["Description"] = markdown(a["Description"])
            add = ""
            add = a.get("Address")[0]
            add = add + ", " + a.get("City")[0]
            add = add + ", " + a.get("State")[0]
            add = add + " " + a.get("Postal")[0]
            a["Directions"] = (
                "https://www.google.com/maps?saddr=My+Location&daddr=" + add
            )
            acc.append(a)
        data["acc"] = acc
        return render_template("accommodations.html", data=data)
    else:
        return redirect(url_for("wedding.home"))


@wedding.route("/colophon")
def colophon():
    if META["Published"]:
        data = META
        META["Path"] = request.path
        data["Colophon"] = markdown(
            AT["meta"].first(fields=["Colophon"])["fields"]["Colophon"]
        )
        return render_template("colophon.html", data=data)
    else:
        return redirect(url_for("wedding.home"))


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


@wedding.route("/rsvp", methods=["GET", "POST"])
def rsvp():
    if META["Published"]:
        data = META
        META["Path"] = request.path
        a = []
        data["attending"] = False
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        else:
            party_id = AT["people"].get(current_user.id)["fields"]["Party"][0]
            data["people"] = []
            data["party"] = AT["parties"].get(party_id)["fields"]
            rsvp_update = []
            emails = []
            yesses = []
            nos = []
            for p in data["party"]["People"]:
                values = {}
                person = AT["people"].get(p)
                values["id"] = person["id"]
                person = person["fields"]

                if "Name" in person:
                    person["FirstName"] = person["Name"].split(" ", 1)[0]
                else:
                    person["FirstName"] = "this person"

                text_fields = ["Name", "FirstName", "AnythingElseDietary", "Email"]
                choice_fields = [
                    "WeddingRSVP",
                    "WelcomeRSVP",
                    "BrunchRSVP",
                    "MBTAPass",
                    "BlueBikesPass",
                    "Shuttle",
                ]
                list_fields = ["Dietary"]

                for field in text_fields:
                    values = check_none(field, person, values, none_val="")

                for field in choice_fields:
                    values = check_none(field, person, values)

                for field in list_fields:
                    values = check_none(field, person, values, none_val=[])
                wedding_rsvp = values["WeddingRSVP"]
                if request.method == "POST":
                    for field in text_fields + choice_fields:
                        values = check_form(field, values, request)
                    for field in list_fields:
                        values = check_form_list(field, values, request)
                    rsvp_update.append(wedding_rsvp != values["WeddingRSVP"])
                    AT["people"].update(
                        values["id"],
                        {
                            "Name": values["Name"],
                            "WeddingRSVP": values["WeddingRSVP"],
                            "WelcomeRSVP": values["WelcomeRSVP"],
                            "BrunchRSVP": values["BrunchRSVP"],
                            "MBTAPass": values["MBTAPass"],
                            "BlueBikesPass": values["BlueBikesPass"],
                            "Shuttle": values["Shuttle"],
                            "AnythingElseDietary": values["AnythingElseDietary"],
                            "Email": values["Email"],
                            "Dietary": values["Dietary"],
                        },
                    )
                    AT["parties"].update(party_id, {"Reply": True})
                data["people"].append(values)
                emails.append(values["Email"])
                if values["WeddingRSVP"] == "Yes":
                    a.append(True)
                    yesses.append(values["FirstName"])
                elif values["FirstName"] != "this person":
                    a.append(False)
                    nos.append(values["FirstName"])

            if any(a):
                data["attending"] = True
            # Removes empty strings (i.e., unknown emails).
            emails = [i for i in emails if i]
            if (request.method == "POST") and not any(rsvp_update):
                if len(emails) > 0:
                    email_confirm(app, yes=yesses, no=nos, recipients=emails)
                    msg = f"""We recorded your response!
                    You should receive email confirmation at
                    {' and '.join(emails)}."""
                else:
                    msg = "We recorded your response!"
                flash(msg)
                return redirect(url_for("wedding.home"))
            return render_template("rsvp.html", data=data)
    else:
        return redirect(url_for("wedding.home"))
