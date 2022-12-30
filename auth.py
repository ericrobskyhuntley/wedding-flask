from flask import Blueprint, request, redirect, url_for, render_template
from flask_login import login_user
from pyairtable.formulas import match
from . import AT, META
from .models import User
auth = Blueprint('auth', __name__)

@auth.route('/login', methods = ['POST'])
def login_post():
    e = None
    name = request.form.get('name')
    if name:
        person = AT["people"].first(formula = match({"Name": name}))
        if not person:
            e = "Name not found. Did you misspell something?"
        else:
            user = User.get(person['id'])
            if user:
                login_user(user, remember = True)
            else:
                e = "Something went wrong."
        return redirect(url_for('wedding.rsvp_post', party_id = person['fields']['Party'][0]))
    else:
        e = "Enter one of your party's names, as it appears on your invitation."
        return e