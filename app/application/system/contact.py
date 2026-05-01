from app.domains.user.service import create_contact_message
from app.integrations.email.client import send_email
from flask import current_app

def send_contact_message_workflow(data, ip_address, user_agent):
    """
    Handles a contact message submission.
    """
    if not all(data.values()):
        return False, "One or more fields are empty!!"

    msg = create_contact_message(
        name=data.get("name"),
        email=data.get("email"),
        subject=data.get("subject"),
        message=data.get("message"),
        ip_address=ip_address,
        user_agent=user_agent
    )

    # Orchestrate admin email notification
    send_email(
        subject=f"[Contact] {data['subject']}",
        recipients=[current_app.config["ADMIN_EMAIL"]],
        reply_to=data["email"],
        body=f"New contact message from {data['name']} <{data['email']}>\n\n{data['message']}"
    )
    
    return True, "Message sent successfully!!"
