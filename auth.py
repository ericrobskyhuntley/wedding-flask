from flask import Blueprint, request, redirect, url_for, render_template
from flask_login import login_user, logout_user, login_required
from pyairtable.formulas import match
from app import AT, META
from models import User

auth = Blueprint('auth', __name__)

@auth.route('/login', methods = ['GET', 'POST'])
def login():
    e = None
    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            person = AT["people"].first(formula = match({"Name": name}))
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
    if META["Path"] in [url_for('wedding.rsvp'), url_for('wedding.itinerary')]:
        return redirect(url_for('wedding.home'))
    else:
        return redirect(META["Path"])
