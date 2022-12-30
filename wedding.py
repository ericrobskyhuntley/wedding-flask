
from flask import render_template, request, url_for, redirect, Blueprint, current_app, flash
from flask_login import login_required, current_user

from pyairtable import Base, Table
from pyairtable.formulas import match
from itertools import groupby
from . import AT, META, dt_parse

# from utils import email_confirm

from dotenv import load_dotenv
import os
load_dotenv()

wedding = Blueprint(
    'wedding', 
    __name__,
    template_folder = 'templates',
    static_folder = 'static'
    )

@wedding.route('/')
def home():
    return render_template('home.html', meta=META)

@wedding.route('/calendar')
def calendar():
    d = []
    for i in AT["events"].all(sort = ["StartTime"]):
        i['fields']['StartTime'] = dt_parse(i['fields']['StartTime'])
        i['fields']['EndTime'] = dt_parse(i['fields']['EndTime'])
        d.append(i['fields'])
    return render_template(
        'calendar.html', 
        meta=META, 
        data=groupby(d, lambda x: x['StartTime'].date())
        )

@wedding.route('/qa')
def qa():
    d = []
    for i in AT["qa"].all(fields = ['Group', 'Question', 'Answer'], sort = ['Group', "Order"]):
        d.append(i['fields'])
    return render_template(
        'qa.html', 
        meta=META, 
        data = groupby(d, lambda x: x['Group'])
        )

@wedding.route('/travel')
def travel():
    return render_template('travel.html', meta=META)


@wedding.route('/colophon')
def colophon():
    return render_template('colophon.html', meta=META)

@wedding.route('/rsvp')
def rsvp():
    e = None
    if current_user.is_authenticated:
        person = AT["people"].first(formula = match({"Name": current_user.name}), fields=["Party"])
        return redirect(url_for('wedding.rsvp_post', party_id = person["fields"]["Party"][0]))
    else:
        return render_template('rsvp.html', error=e, meta=META)

@wedding.route('/rsvp/<party_id>', methods = ['GET', 'POST'])
def rsvp_post(party_id):
    guest_list = []
    e = None
    print(party_id)
    party = AT["parties"].get(party_id)["fields"]
    for person in party['People']:
        values = {}
        g = AT["people"].get(person)
        values["id"] = g["id"]
        g = g["fields"]
        if "Name" not in g:
            values["Name"] = ""
        else:
            values["Name"] = g["Name"]
        if "RSVP" not in g:
            values["RSVP"] = None
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
        
        values["name_id"] = "-".join(["name", values["id"]])
        values["rsvp_id"] = "-".join(["rsvp", values["id"]])
        values["email_id"] = "-".join(["email", values["id"]])
        values["meal_id"] = "-".join(["meal", values["id"]])
        values["ae_id"] = "-".join(["ae", values["id"]])

        if request.method == 'POST':
            if values["rsvp_id"] in request.form:
                if request.form[values["rsvp_id"]] == "y":
                    values["RSVP"] = "Yes"
                elif request.form[values["rsvp_id"]] == "n":
                    values["RSVP"] = "No"
                else:
                    values["RSVP"] = None
            if values["name_id"] in request.form:
                values["Name"] = request.form[values["name_id"]]
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
                "Name": values["Name"],
                "RSVP": values["RSVP"],
                "Email": values["Email"],
                "Meal": values["Meal"],
                "AnythingElse": values["AnythingElse"]
                })
      
        guest_list.append(values)
    # if values["Meal"] and request.method == 'POST':
    #     AT["parties"].update(party_id, {
    #         "Reply": True
    #         })
    
    return render_template('rsvp.html', party = party, people = guest_list, error = e, meta=META)
    #     email_confirm(current_app, guest_list, META)
    # except:
    #     e = "There is no party with that ID."