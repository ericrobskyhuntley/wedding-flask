from flask import Flask, render_template, request, url_for, flash, redirect
from datetime import datetime
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'd16746eaacdbe452ae4e4ba03f4be835a35e1afd1c4e783d'

airtable = {
    "api_key": "keyQlbV7yvwwGAadl",
    "app_key": "appq8TUMTdg1V0Dww",
    "meta": "Meta",
    "venues": "Venues",
    "calendar": "Events",
    "people": "People"
}

messages = [{'title': 'Message One',
             'content': 'Message One Content'},
            {'title': 'Message Two',
             'content': 'Message Two Content'}
            ]

def unique(l):
    return list(set(l))

def dt_parse(string):
    return {
        "date": datetime.strptime(string, "%Y-%m-%dT%H:%M:%S.000Z").date(),
        "time": datetime.strptime(string, "%Y-%m-%dT%H:%M:%S.000Z").time()
    }

META = requests.get(
    f"https://api.airtable.com/v0/{airtable['app_key']}/{airtable['meta']}", 
    headers = {
        f"Authorization": f"Bearer {airtable['api_key']}",
        }
    ).json()['records'][0]['fields']

META['Times'] = unique(
    [dt_parse(i)['date'] for i in META['Times']]
    )

@app.route('/')
def home():
    
    # dataset = []
    # for i in dict['records']:
    #      dict = i['fields']
    #      dataset.append(dict)
    
    return render_template('home.html', meta=META)

@app.route('/calendar')
def calendar():
    r = requests.get(
        f"https://api.airtable.com/v0/{airtable['app_key']}/{airtable['calendar']}", 
        headers = {
            f"Authorization": f"Bearer {airtable['api_key']}",
            }
        ).json()
    
    d = []
    for i in r['records']:
        d.append(i['fields'])
    return render_template('calendar.html', meta=META, data = d)

@app.route('/travel')
def travel():
    return render_template('travel.html', meta=META)

@app.route('/rsvp', methods = ('GET', 'POST'))
def rsvp():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        elif not content:
            flash('Content is required!')
        else:
            messages.append({'title': title, 'content': content})
            return redirect(url_for('home'))
    return render_template('rsvp.html', meta=META)
