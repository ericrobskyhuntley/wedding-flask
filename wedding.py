
from flask import render_template, request, url_for, redirect, Blueprint, current_app, flash
from pyairtable import Base, Table
from pyairtable.formulas import match
from datetime import datetime
from itertools import groupby

from utils import email_confirm

from dotenv import load_dotenv
import os
load_dotenv()

wedding = Blueprint(
    'wedding', 
    __name__,
    template_folder = 'templates',
    static_folder = 'static'
    )


BASE = Base(os.getenv("AT_KEY"), os.getenv("AT_BASE_ID"))

AT = {
    "venues": Table(os.getenv("AT_KEY"), os.getenv("AT_BASE_ID"), "Venues"),
    "events": Table(os.getenv("AT_KEY"), os.getenv("AT_BASE_ID"), "Events"),
    "people": Table(os.getenv("AT_KEY"), os.getenv("AT_BASE_ID"), "People"),
    "parties": Table(os.getenv("AT_KEY"), os.getenv("AT_BASE_ID"), "Parties"),
    "qa": Table(os.getenv("AT_KEY"), os.getenv("AT_BASE_ID"), "QA"),
    "meta": Table(os.getenv("AT_KEY"), os.getenv("AT_BASE_ID"), "Meta")
}

def unique(l):
    return list(set(l))

def dt_parse(string):
    return {
        "date": datetime.strptime(string, "%Y-%m-%dT%H:%M:%S.000Z").date(),
        "time": datetime.strptime(string, "%Y-%m-%dT%H:%M:%S.000Z").time()
    }

META = AT["meta"].first()['fields']

META['Times'] = [dt_parse(i)['date'] for i in META['Times']]
META['Names'] = " & ".join(META['Names'])

@wedding.route('/')
def home():
    return render_template('home.html', meta=META)

@wedding.route('/calendar')
def calendar():
    d = []
    for i in AT["events"].all(sort = ["Time"]):
        d.append(i['fields'])
    return render_template('calendar.html', meta=META, data = d)

@wedding.route('/qa')
def qa():
    d = []
    for i in AT["qa"].all(fields = ['Group', 'Question', 'Answer'], sort = ['Group', "Order"]):
        d.append(i['fields'])
    dt = groupby(d, lambda c: c['Group'])
    print(dt)
    return render_template('qa.html', meta=META, data = dt)

@wedding.route('/travel')
def travel():
    return render_template('travel.html', meta=META)


@wedding.route('/colophon')
def colophon():
    return render_template('colophon.html', meta=META)

@wedding.route('/reply/<party_id>', methods = ['GET', 'POST'])
def reply(party_id):
    guest_list = []
    e = None
    party = AT["parties"].get(party_id)["fields"]
    for p in party['People']:
        values = {}
        g = AT["people"].get(p)
        values["id"] = g["id"]
        g = g["fields"]
        values["Name"] = g["Name"]
        if "RSVP" not in g:
            values["RSVP"] = False
        else:
            values["RSVP"] = g["RSVP"]
        if "Email" not in g:
            values["Email"] = None
        else:
            values["Email"] = g["Email"]
        if "Meal" not in g:
            values["Meal"] = None
        else:
            values["Meal"] = g["Meal"]
        if "AnythingElse" not in g:
            values["AnythingElse"] = ""
        else:
            values["AnythingElse"] = g["AnythingElse"]
        
        values["rsvp_id"] = "-".join(["rsvp", values["id"]])
        values["email_id"] = "-".join(["email", values["id"]])
        values["meal_id"] = "-".join(["meal", values["id"]])
        values["ae_id"] = "-".join(["ae", values["id"]])

        if request.method == 'POST':
            if values["rsvp_id"] in request.form:
                if request.form[values["rsvp_id"]] == "yes":
                    values["RSVP"] = True
                else:
                    values["RSVP"] = False
            if values["email_id"] in request.form:
                values["Email"] = request.form[values["email_id"]]
            if values["meal_id"] in request.form:
                if request.form[values["meal_id"]] == "veggie":
                    values["Meal"] = ["Vegetarian"]
                else:
                    values["Meal"] = ["Vegan"]
            if values["ae_id"] in request.form:
                values["AnythingElse"] = request.form[values["ae_id"]]
            AT["people"].update(values["id"], {
                "RSVP": values["RSVP"],
                "Email": values["Email"],
                "Meal": values["Meal"],
                "AnythingElse": values["AnythingElse"]
                })
            AT["parties"].update(party_id, {
                "Reply": True
                })
        guest_list.append(values)
    if values["Meal"] and request.method == 'POST':
        return redirect(url_for('wedding.home'))
    else:
        return render_template('reply.html', party = party, people = guest_list, error = e, meta=META)
    #     email_confirm(current_app, guest_list, META)
    # except:
    #     e = "There is no party with that ID."

@wedding.route('/rsvp', methods = ['GET', 'POST'])
def rsvp():
    e = None
    guest_list = []
    if request.method == 'POST':
        name = request.form['name']
        if name:
            person = AT["people"].first(formula= match({"Name": name}), fields=["Party"])
            if not person:
                e = "Name not found. Did you misspell something?"
            else:
                return redirect(url_for('wedding.reply', party_id = person["fields"]["Party"][0]))
        else:
            e = "Enter one of your party's names, as it appears on your invitation."
    return render_template('rsvp.html', people = guest_list, error = e, meta=META)