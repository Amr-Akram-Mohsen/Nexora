from app.integrations.email.client import send_email
from flask import current_app

def send_admin_email(data):
    send_email(
        subject=f"[Contact] {data['subject']}",
        recipients=[current_app.config["ADMIN_EMAIL"]],
        reply_to=data["email"],
        body=f"""
New contact message

From: {data['name']} <{data['email']}>

Message:
{data['message']}
"""
    )
def create_contact_message(name, email, subject, message, ip_address, user_agent):
    from app.domains.user.models import ContactMessage
    from app.core.extensions import db
    msg = ContactMessage(
        name=name,
        email=email,
        subject=subject,
        message=message,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.session.add(msg)
    db.session.commit()
    return msg
