from flask_mail import Mail, Message
from flask import render_template
from functools import partial

def email_confirm(app, guest_list, meta):
    mail = Mail(app)

    msg = Message(
        "Thanks for your RSVP!",
        sender = "ericrobskyhuntley@gmail.com",
        reply_to = "ericrobskyhuntley@gmail.com,tmfox09@gmail.com"
        )

    # if app.config["DEBUG"]:
    msg.recipients = ['ericrobskyhuntley@gmail.com']
    # else:
    #     msg.recipients = [form["email"]]
    #     msg.cc = ["wedding@davenquinn.com"]

    _ = partial(
        render_template,
        guest_list = guest_list,
        meta = meta
        )

    msg.body = _("email/confirmation.txt")
    mail.send(msg)