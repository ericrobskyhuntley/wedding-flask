from flask import render_template, request, url_for, redirect, Blueprint, flash, send_from_directory
from flask_login import current_user, login_user, logout_user, login_required

from markdown import markdown
from pyairtable.formulas import match, Field, EQ
from itertools import groupby
import os

from .models import User
from .helpers import dt_parse, email_confirm, get_meta, process_events, compose_formula, check_form, check_form_list, check_none
from . import wedding, auth, META, AT

META["Path"] = None

@wedding.route("/")
def index():
    data = META
    META["Path"] = request.path
    data["LandingText"] = markdown(
        AT["meta"].first(fields=["LandingText"])["fields"]["LandingText"]
    )
    return render_template("home.html", data=data)

@wedding.route("/robots.txt")
def robots_txt():
    return send_from_directory(os.path.join(wedding.root_path, "static"), "robots.txt")


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
        return redirect("/")


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
        return redirect("/")


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
        return redirect("/")


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
        return redirect("/")


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
                return redirect("/")
            return render_template("rsvp.html", data=data)
    else:
        return redirect("/")

@auth.route('/login', methods = ['GET', 'POST'])
def login():
    e = None
    if request.method == 'POST':
        name = request.form.get('name')
        name_prepared = name.replace(" ", "").replace("-", "").lower()
        if name:
            person = AT["people"].first(formula = match({"Slug": name_prepared}))
            if (not person) or ("Party" not in person["fields"]):
                e = "Name not found. Did you misspell something?"
            else:
                user = User.get(person['id'])
                if user:
                    logout_user()
                    login_user(user, remember = True)
                else:
                    e = "Something went wrong."
                return redirect(META["Path"])
        else:
            e = "Enter one of your party's names, as it appears on your invitation."
    return render_template(
        'login.html', 
        error = e, 
        data = META
        )

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')