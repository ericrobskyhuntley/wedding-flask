
from flask import render_template, request, url_for, redirect, Blueprint
from flask_login import current_user

from slugify import slugify
from pyairtable.formulas import match, FIELD, FIND, STR_VALUE, OR, EQUAL
from itertools import groupby
from app import AT, META, dt_parse

# from utils import email_confirm

META["Path"] = None

wedding = Blueprint(
    'wedding', 
    __name__,
    template_folder = 'templates',
    static_folder = 'static'
    )

@wedding.route('/')
def home_redirect():
    return redirect(url_for('wedding.home'))


@wedding.route('/home')
def home():
    META["Path"] = request.path
    return render_template('home.html', meta=META)

def process_events(events):
    d = []
    for e in events:
        e['fields']['StartTime'] = dt_parse(e['fields']['StartTime'])
        e['fields']['EndTime'] = dt_parse(e['fields']['EndTime'])
        e['fields']['Slug'] = slugify(e['fields']['Name'])
        d.append(e['fields'])
    return d

def compose_formula(list, field):
    f = []
    for term in list:
        f.append(FIND(STR_VALUE(term), 'ARRAYJOIN(' + FIELD(field) + ')'))
    f.append(EQUAL(0, FIELD(field)))
    return OR(','.join(f))

@wedding.route('/itinerary')
def itinerary():
    if META["Published"]:
        META['Path'] = request.path
        if current_user.is_authenticated:
            person = AT["people"].get(current_user.id).get("fields")
            if "GroupNames" in person:
                formula = compose_formula(person["GroupNames"], "LimitedInviteNames")
            else:
                formula = EQUAL(0, FIELD("LimitedInviteNames"))
            events = AT["events"].all(formula = formula, sort = ["StartTime"])
            d = process_events(events)
            return render_template(
                'itinerary.html', 
                meta=META, 
                data=groupby(d, lambda x: x['StartTime'].date())
                )
        else:
            return redirect(url_for('auth.login'))
    else:
        return redirect(url_for('wedding.home'))

@wedding.route('/qa')
def qa():
    if META["Published"]:
        META["Path"] = request.path
        d = []
        for i in AT["qa"].all(fields = ['Group', 'Question', 'Answer'], sort = ['Group', "Order"]):
            d.append(i['fields'])
        return render_template(
            'qa.html', 
            meta=META, 
            data = groupby(d, lambda x: x['Group'])
            )
    else:
        return redirect(url_for('wedding.home'))

@wedding.route('/travel/accommodations')
def accommodations():
    if META["Published"]:
        META["Path"] = request.path
        data = AT["accommodations"].first().get("fields")
        return render_template('accommodations.html', data = data, meta=META)
    else:
        return redirect(url_for('wedding.home'))


@wedding.route('/travel/getting_around/')
def getting_around():
    if META["Published"]:
        META["Path"] = request.path
        return render_template('travel.html', meta=META)
    else:
        return redirect(url_for('wedding.home'))


@wedding.route('/travel/things_to_do/')
def things_to_do():
    if META["Published"]:
        META["Path"] = request.path
        return render_template('travel.html', meta=META)
    else:
        return redirect(url_for('wedding.home'))


@wedding.route('/colophon')
def colophon():
    if META["Published"]:
        META["Path"] = request.path
        return render_template('colophon.html', meta=META)
    else:
        return redirect(url_for('wedding.home'))

@wedding.route('/rsvp', methods = ['GET', 'POST'])
def rsvp():
    if META["Published"]:
        META['Path'] = request.path
        e = None
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        else:
            party_id = AT["people"].first(
                formula = match(
                    {"Name": current_user.name}
                    ), 
                fields=["Party"]
                )["fields"]["Party"][0]
            guest_list = []
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
                    AT["parties"].update(party_id, {
                    "Reply": True
                    })
                guest_list.append(values)
            return render_template('rsvp.html', party = party, people = guest_list, error = e, meta=META)
    else:
        return redirect(url_for('wedding.home'))
    
    
    #     email_confirm(current_app, guest_list, META)
    # except:
    #     e = "There is no party with that ID."
