
from flask import render_template, request, url_for, redirect, Blueprint
from flask_login import current_user

from markdown import markdown
from slugify import slugify
from pyairtable.formulas import match, FIELD, FIND, STR_VALUE, OR, EQUAL
from itertools import groupby
from operator import itemgetter
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
    data = META
    data["Path"] = request.path
    return render_template(
        'home.html', 
        data = data
        )

def process_events(events):
    d = []
    for e in events:
        e = e['fields']
        if "Description" in e:
            e['Description'] = markdown(e['Description'])
        else:
            e['Description'] = ''
        if "VenueName" not in e:
            e['VenueName'] = "To be announced!"
        e['StartTime'] = dt_parse(e['StartTime'])
        e['EndTime'] = dt_parse(e['EndTime'])
        e['Slug'] = slugify(e['Name'])
        if "Artists" in e:
            artists = []
            for artist in e["Artists"]:
                a = AT["vendors"].get(artist)['fields']
                art = {} 
                art['Website'] = a.get('Website')
                art['Name'] = a.get('Name')
                art['Role'] = a.get('Role')
                if 'Status' in a:
                    if a['Status'] == 'Confirmed':
                        artists.append(art)
            artists = sorted(artists, key = itemgetter('Role'))
            a_dict = {}
            for role, artist in groupby(artists, key = itemgetter('Role')):
                a_dict[role] = list(artist)
            e['Artists'] = a_dict
        d.append(e)
    
    results = groupby(d, lambda x: x['StartTime'].date())
    return results

def compose_formula(list, field):
    f = []
    for term in list:
        f.append(FIND(STR_VALUE(term), 'ARRAYJOIN(' + FIELD(field) + ')'))
    f.append(EQUAL(0, FIELD(field)))
    return OR(','.join(f))

@wedding.route('/itinerary')
def itinerary():
    if META["Published"]:
        data = META
        data['Path'] = request.path
        if current_user.is_authenticated:
            person = AT["people"].get(current_user.id).get("fields")
            if "GroupNames" in person:
                formula = compose_formula(person["GroupNames"], "LimitedInviteNames")
            else:
                formula = EQUAL(0, FIELD("LimitedInviteNames"))
            events = AT["events"].all(formula = formula, sort = ["StartTime"])
            
            itinerary = []
            for date, event in process_events(events):
                d = {}
                d['Date'] = date
                venues = []
                for v, e in groupby(event, lambda x: {
                    'VenueName': x['VenueName'][0],
                    'VenueAddress': x['VenueAddress'][0], 
                    'VenueCity': x['VenueCity'][0], 
                    'VenueState': x['VenueState'][0], 
                    'VenuePostal': x['VenuePostal'][0], 
                    'VenueURL': x['VenueURL'][0], 
                    'Lat': x['Lat'][0], 
                    'Lng': x['Lng'][0]}):
                    venue = v
                    es = []
                    for i in e:
                        es.append(i)
                    venue['Slug'] = v['VenueName'].lower().replace(' ', '_').replace("'", '_')
                    venue["Events"] = es
                    venues.append(venue)
                d['Venues'] = venues
                itinerary.append(d)
            data['itinerary'] = itinerary
            from pprint import pprint
            pprint(data)
            return render_template(
                'itinerary.html', 
                data = data
                )
        else:
            return redirect(url_for('auth.login'))
    else:
        return redirect(url_for('wedding.home'))

@wedding.route('/qa')
def qa():
    if META["Published"]:
        data = META
        data["Path"] = request.path
        d = []
        for i in AT["qa"].all(formula=EQUAL(1, FIELD("Publish"))):
            i = i['fields']
            i['Question'] = markdown(i['Question'])
            i['Answer'] = markdown(i['Answer'])
            d.append(i)
        data["qa"] = d
        return render_template(
            'qa.html', 
            data = data
            )
    else:
        return redirect(url_for('wedding.home'))

@wedding.route('/travel/accommodations')
def accommodations():
    if META["Published"]:
        data = META
        data["Path"] = request.path
        acc = []
        for a in AT["accommodations"].all(formula=EQUAL(1, FIELD("Listed"))):
            a = a['fields']
            a['Name'] = a['Name'][0]
            a['Slug'] = a['Name'].lower().replace(' ', '_').replace("'", '_')
            a['Website'] = a['Website'][0]
            a['Description'] = markdown(a['Description'])
            acc.append(a)
        data['acc'] = acc
        return render_template(
            'accommodations.html', 
            data = data
            )
    else:
        return redirect(url_for('wedding.home'))


@wedding.route('/travel/getting-around/')
def getting_around():
    if META["Published"]:
        data = META
        data["Path"] = request.path
        data['GettingAround'] = markdown(
            AT['meta'].first(
                fields = ['GettingAround']
                )['fields']['GettingAround']
            )
        return render_template(
            'getting-around.html',
            data = data
            )
    else:
        return redirect(url_for('wedding.home'))


@wedding.route('/travel/things-to-do/')
def things_to_do():
    if META["Published"]:
        data = META
        data["Path"] = request.path
        return render_template(
            'travel.html', 
            data = data
            )
    else:
        return redirect(url_for('wedding.home'))


@wedding.route('/colophon')
def colophon():
    if META["Published"]:
        data = META
        data["Path"] = request.path
        data['Colophon'] = markdown(
            AT['meta'].first(fields=['Colophon'])['fields']['Colophon']
            )
        return render_template(
            'colophon.html', 
            data = data
            )
    else:
        return redirect(url_for('wedding.home'))

def check_none(field, values, values_dict, none_val = None):
    field_lc = field.lower()
    field_id = "_".join([field_lc, "id"])
    values_dict[field_id] = "_".join([field_lc, values_dict["id"]])
    if field not in values:
        values_dict[field] = none_val
    else:
        values_dict[field] = values[field]
    return values_dict

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

@wedding.route('/rsvp', methods = ['GET', 'POST'])
def rsvp():
    if META["Published"]:
        data = META
        data['Path'] = request.path
        a = []
        data["attending"] = False
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        else:
            party_id = AT["people"].get(current_user.id)["fields"]["Party"][0]
            data["people"] = []
            data["party"] = AT["parties"].get(party_id)["fields"]
            for p in data["party"]['People']:
                values = {}
                person = AT["people"].get(p)
                values["id"] = person["id"]
                person = person["fields"]

                text_fields = ["Name", "AnythingElse"]
                choice_fields = ["WeddingRSVP", "WelcomeRSVP", "BagelsRSVP", "Email", "Meal"]

                for field in text_fields:
                    values = check_none(field, person, values, none_val = "")

                for field in choice_fields:
                    values = check_none(field, person, values)

                if request.method == 'POST':
                    for field in text_fields + choice_fields:
                        values = check_form(field, values, request)
                    AT["people"].update(values["id"], {
                        "Name": values["Name"],
                        "WeddingRSVP": values["WeddingRSVP"],
                        "WelcomeRSVP": values["WelcomeRSVP"],
                        "BagelsRSVP": values["BagelsRSVP"],
                        "Email": values["Email"],
                        "Meal": values["Meal"],
                        "AnythingElse": values["AnythingElse"]
                        })
                    AT["parties"].update(party_id, {
                        "Reply": True
                    })
                data["people"].append(values)
                if values["WeddingRSVP"] == "Yes":
                    a.append(True)
                else:
                    a.append(False)
            if(any(a)):
                # attending = True
                data["attending"] = True
            return render_template(
                'rsvp.html',
                data = data
                )
    else:
        return redirect(url_for('wedding.home'))
