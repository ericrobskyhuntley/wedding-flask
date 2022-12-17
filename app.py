from flask import Flask, render_template, request, url_for, flash, redirect
from pyairtable import Base, Table
from pyairtable.formulas import match
from datetime import datetime
from itertools import groupby

from dotenv import load_dotenv
import os
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

BASE = Base(os.getenv("AT_KEY"), os.getenv("AT_BASE_ID"))

airtable = {
    "venues": "Venues",
    "calendar": "Events",
    "people": "People",
    "qa": "QA"
}

def unique(l):
    return list(set(l))

def dt_parse(string):
    return {
        "date": datetime.strptime(string, "%Y-%m-%dT%H:%M:%S.000Z").date(),
        "time": datetime.strptime(string, "%Y-%m-%dT%H:%M:%S.000Z").time()
    }

META = BASE.first("Meta")['fields']

META['Times'] = [dt_parse(i)['date'] for i in META['Times']]

@app.route('/')
def home():
    print(META)
    return render_template('home.html', meta=META)

@app.route('/calendar')
def calendar():
    d = []
    for i in BASE.all("Events", sort = ['Time']):
        d.append(i['fields'])
    return render_template('calendar.html', meta=META, data = d)

@app.route('/qa')
def qa():
    d = []
    for i in BASE.all("QA", fields = ['Group', 'Question', 'Answer'], sort = ['Group', "Order"]):
        d.append(i['fields'])
    dt = groupby(d, lambda c: c['Group'])
    print(dt)
    return render_template('qa.html', meta=META, data = dt)

@app.route('/travel')
def travel():
    return render_template('travel.html', meta=META)


@app.route('/colophon')
def colophon():
    return render_template('colophon.html', meta=META)

@app.route('/rsvp', methods = ['GET', 'POST'])
def rsvp():
    e = None
    d = None
    if request.method == 'POST':
        email = request.form['email']
        if email:
            d = BASE.first("People", formula= match({"Email": email}))
            if not d:
                e = "Email not found. Did you misspell something?"
            else:
                if "RSVP" not in d["fields"]:
                    d["fields"]["RSVP"] = False
                if 'rsvp' in request.form:
                    if request.form['rsvp'] == "yes":
                        rsvp = True
                        Table(os.getenv("AT_KEY"), os.getenv("AT_BASE_ID"), "People").update(d['id'], {"RSVP": rsvp})
                    else:
                        rsvp = False
                        Table(os.getenv("AT_KEY"), os.getenv("AT_BASE_ID"), "People").update(d['id'], {"RSVP": rsvp})
                    d["fields"]["RSVP"] = rsvp
        else:
            e = "Enter an email address."
    return render_template('rsvp.html', data = d, error = e, meta=META)

