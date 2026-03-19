from flask import Flask
from flask_login import LoginManager
from flask_sitemap import Sitemap

from typing import Optional
import os

from wedding_flask.models import User
from wedding_flask.helpers import dt_parse
from wedding_flask import wedding, auth, AT
    
app = Flask(
    __name__,
    static_folder="wedding_flask/static",
    template_folder="wedding_flask/templates"
    )
ext = Sitemap(app=app)

app.register_blueprint(wedding)
app.register_blueprint(auth)

app.config.update(
    MAIL_SERVER = os.getenv("MAIL_SERVER"),
    MAIL_PORT = os.getenv("MAIL_PORT"),
    MAIL_USE_SSL = True,
    MAIL_USERNAME = os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config['SITEMAP_INCLUDE_RULES_WITHOUT_PARAMS'] = True

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id) -> Optional[User]:
    return User.get(user_id)


