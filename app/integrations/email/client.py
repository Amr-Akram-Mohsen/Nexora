from flask_mail import Message
from flask import current_app
from app.core.extensions import mail

def send_email(subject, recipients, body, reply_to=None):
    if not current_app.config.get("MAIL_ENABLED", True):
        current_app.logger.info("MAIL_ENABLED=False, skipping email")
        return

    msg = Message(
        subject=subject,
        sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
        recipients=recipients,
        reply_to=reply_to,
        body=body
    )

    try:
        mail.send(msg)
    except Exception as e:
        current_app.logger.error("Failed to send email: %s", e)
