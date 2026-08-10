import logging
from flask_mail import Message
from flask import current_app
from app.core.extensions import mail

logger = logging.getLogger(__name__)

def send_email(subject: str, recipients: list[str], body: str, html: str = None, reply_to: str = None) -> bool:
    """
    Sends an email using the Flask-Mail extension.
    Returns True on success, False on failure or if mail is disabled.
    """
    if not current_app.config.get("MAIL_ENABLED", False):
        logger.info("[AUTH] MAIL_ENABLED=False — skipping actual SMTP for %s | subject: %s", recipients, subject)
        logger.info("[AUTH] Email Body:\n%s", body)
        return True

    msg = Message(
        subject=subject,
        sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
        recipients=recipients,
        reply_to=reply_to,
        body=body,
        html=html
    )

    try:
        mail.send(msg)
        logger.info("[AUTH] Email sent successfully to %s | subject: %s", recipients, subject)
        return True
    except Exception as e:
        logger.error("[AUTH] Failed to send email to %s | subject: %s | error: %s", recipients, subject, str(e), exc_info=True)
        return False
