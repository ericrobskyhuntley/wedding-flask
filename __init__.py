from flask import Flask
from flask_login import LoginManager
from pyairtable import Base, Table

from typing import Optional
from datetime import datetime, timezone
from markdown import markdown
import pytz
import os

from dotenv import load_dotenv
load_dotenv()

def unique(l):
    return list(set(l))

def dt_parse(string):
    return datetime.strptime(string, "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).astimezone(pytz.timezone('America/New_York'))

AT = {
    "venues": Table(os.getenv("AT_KEY"), os.getenv("AT_BASE_ID"), "Venues"),
    "events": Table(os.getenv("AT_KEY"), os.getenv("AT_BASE_ID"), "Events"),
    "people": Table(os.getenv("AT_KEY"), os.getenv("AT_BASE_ID"), "People"),
    "parties": Table(os.getenv("AT_KEY"), os.getenv("AT_BASE_ID"), "Parties"),
    "qa": Table(os.getenv("AT_KEY"), os.getenv("AT_BASE_ID"), "QA"),
    "meta": Table(os.getenv("AT_KEY"), os.getenv("AT_BASE_ID"), "Meta"),
    "artists": Table(os.getenv("AT_KEY"), os.getenv("AT_BASE_ID"), "Artists"),
    "accommodations": Table(os.getenv("AT_KEY"), os.getenv("AT_BASE_ID"), "Accommodations")
}

META = AT["meta"].first(fields=['Published', 'Times', 'Names', 'Cities', 'Colophon', 'Registry', 'UnderConstructionImage'])['fields']
META['UniqueDates'] = unique([dt_parse(datetime).date() for datetime in META['Times']])
# META['MinDate'] = min(META['UniqueDates'])
# META['MaxDate'] = max(META['UniqueDates'])
META['ShortNames'] = [name.split()[0] for name in META['Names']]
META['Colophon'] = markdown(META['Colophon'])
META['Path'] = 'wedding.home'
if "Published" not in META:
    META["Published"] = False

print(META)

BASE = Base(os.getenv("AT_KEY"), os.getenv("AT_BASE_ID"))

def create_app():
    app = Flask(__name__)

    from .wedding import wedding as wedding_bp
    app.register_blueprint(wedding_bp)

    from .auth import auth as auth_bp
    app.register_blueprint(auth_bp)

    app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER")
    app.config["MAIL_PORT"] = os.getenv("MAIL_PORT")
    app.config["MAIL_USE_SSL"] = os.getenv("MAIL_USE_SSL")
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    
    from .models import User
    @login_manager.user_loader
    def load_user(user_id) -> Optional[User]:
        return User.get(user_id)

    return app



