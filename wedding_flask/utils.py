from flask_mail import Mail, Message
from flask import render_template
from functools import partial
import os

from .config import META

def email_confirm(app, yes , no, recipients):
    mail = Mail(app)

    rsvp = Message(
        f"{' & '.join(META['ShortNames'])} | Thanks for your RSVP!",
        sender = os.getenv("MAIL_USERNAME"),
        cc = [os.getenv("MAIL_USERNAME")],
        recipients = recipients
        )

    _ = partial(
        render_template,
        yes = yes,
        no = no,
        meta = META
        )

    rsvp.html = _("rsvp_conf.html")
    mail.send(rsvp)
    return