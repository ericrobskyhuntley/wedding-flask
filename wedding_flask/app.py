from flask import Flask
from flask_login import LoginManager

from typing import Optional
from markdown import markdown
import os

from .config import AT
from .models import User
from .helpers import dt_parse
    
app = Flask(__name__)

from .wedding import wedding as wedding_bp
app.register_blueprint(wedding_bp)

from .auth import auth as auth_bp
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

@login_manager.user_loader
def load_user(user_id) -> Optional[User]:
    return User.get(user_id)


