# app/services/mailer.py
from flask import current_app
from flask_mail import Message
from app.extensions import mail


def send_admin_email(data):
    if not current_app.config.get("MAIL_ENABLED", True):
        current_app.logger.info("MAIL_ENABLED=False, skipping email")
        return    

    msg = Message(
        subject=f"[Contact] {data['subject']}",
        sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
        recipients=[current_app.config["ADMIN_EMAIL"]],
        reply_to=data["email"],
        body=f"""
New contact message

From: {data['name']} <{data['email']}>

Message:
{data['message']}
"""
    )

    try:
        mail.send(msg)
    except Exception as e:
        # Log it but don't crash the route
        current_app.logger.error("Failed to send contact email: %s", e)
