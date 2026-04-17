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
