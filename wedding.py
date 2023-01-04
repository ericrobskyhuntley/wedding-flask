
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
        e = e['fields']
        e['StartTime'] = dt_parse(e['StartTime'])
        e['EndTime'] = dt_parse(e['EndTime'])
        e['Slug'] = slugify(e['Name'])
        if "Artists" in e:
            artists = []
            for a in e["Artists"]:
                artist = AT["artists"].get(a)['fields']
                if 'Status' in artist:
                    if artist['Status'] == 'Confirmed':
                        artists.append(artist)
            e['Artists'] = artists
        d.append(e)
    print(d)
    return groupby(d, lambda x: x['StartTime'].date())

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
            return render_template(
                'itinerary.html', 
                meta=META, 
                data=process_events(events)
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
        META['Path'] = request.path
        e = None
        a = []
        attending = False
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        else:
            party_id = AT["people"].get(current_user.id)["fields"]["Party"][0]
            people = []
            party = AT["parties"].get(party_id)["fields"]
            for p in party['People']:
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
                people.append(values)
                if values["WeddingRSVP"] == "Yes":
                    a.append(True)
                else:
                    a.append(False)
            if(any(a)):
                attending = True
            return render_template('rsvp.html', party = party, people = people, attending = attending, error = e, meta=META)
    else:
        return redirect(url_for('wedding.home'))
    
    
    #     email_confirm(current_app, guest_list, META)
    # except:
    #     e = "There is no party with that ID."
