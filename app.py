from flask import Flask
from flask_login import LoginManager
from pyairtable import Api

from typing import Optional
from datetime import datetime, timezone
from markdown import markdown
import pytz
import os


from dotenv import load_dotenv
load_dotenv()

api = Api(os.getenv("AT_KEY"))

def unique(l):
    return list(set(l))

def dt_parse(string):
    return datetime.strptime(string, "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(pytz.timezone('America/New_York'))

AT = {
    "venues": api.table(os.getenv("AT_BASE_ID"), "Venues"),
    "events": api.table(os.getenv("AT_BASE_ID"), "Events"),
    "people": api.table(os.getenv("AT_BASE_ID"), "People"),
    "parties": api.table(os.getenv("AT_BASE_ID"), "Parties"),
    "qa": api.table(os.getenv("AT_BASE_ID"), "QA"),
    "meta": api.table(os.getenv("AT_BASE_ID"), "Meta"),
    "vendors": api.table(os.getenv("AT_BASE_ID"), "Vendors"),
    "accommodations": api.table(os.getenv("AT_BASE_ID"), "Accommodations"),
    "thingsToDo": api.table(os.getenv("AT_BASE_ID"), "ThingsToDo")
}

META = AT["meta"].first(
    fields = ['Published', 
              'Times', 
              'Names', 
              'Cities', 
              'Registry',
              'States',
              'SiteURL']
              )['fields']
META["CityStates"] = unique([c + ", " + s for c, s in zip(META["Cities"], META["States"])])
META['UniqueDates'] = unique([dt_parse(dt).date() for dt in META['Times']])
META['ShortNames'] = [n.split()[0] for n in META['Names']]
META['ThingsToDo'] = AT['thingsToDo'].all()

# Remove extraneous keys.
for key in ["Cities", "States", "Times"]:
    del META[key]
    
META['Path'] = 'wedding.home'

if "Published" not in META:
    META["Published"] = False
    
app = Flask(__name__)

from wedding import wedding as wedding_bp
app.register_blueprint(wedding_bp)

from auth import auth as auth_bp
app.register_blueprint(auth_bp)

app.config.update(
    MAIL_SERVER = os.getenv("MAIL_SERVER"),
    MAIL_PORT = os.getenv("MAIL_PORT"),
    MAIL_USE_SSL = True,
    MAIL_USERNAME = os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

from models import User
@login_manager.user_loader
def load_user(user_id) -> Optional[User]:
    return User.get(user_id)


