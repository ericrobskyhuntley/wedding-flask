from flask import Flask
from wedding import wedding

from dotenv import load_dotenv
import os
load_dotenv()

app = Flask(__name__)
app.register_blueprint(wedding)

app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER")
app.config["MAIL_PORT"] = os.getenv("MAIL_PORT")
app.config["MAIL_USE_SSL"] = os.getenv("MAIL_USE_SSL")
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")