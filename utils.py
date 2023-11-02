from flask_mail import Mail, Message
from flask import render_template
from functools import partial
from app import META
import os

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

def address_if_blank(existing, new_col, new_dict, concat_string = ", "):
    """
    concatenates values of a dict based on whether value exists.
    """
    if new_col in new_dict:
        if len(existing) > 0:
            existing = existing + concat_string + new_dict[new_col]
        else:
            existing = new_dict[new_col]
    return existing