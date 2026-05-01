from app.domains.user.service import (
    create_user,
    get_user_by_email,
    get_newsletter_subscriber_by_email,
    link_newsletter_subscriber_to_user
)
from app.application.user.email_service import send_verification_email
from app.application.interaction.newsletter import subscribe_workflow

def register_user_workflow(name, email, password, wants_newsletter=False):
    """
    Handles the full registration workflow.
    """
    if get_user_by_email(email):
        return None, "An account with this email already exists."

    # Create user
    user, verification_token = create_user(name, email, password)
    
    # Newsletter opt-in (Reuse standalone workflow)
    newsletter_msg = None
    if wants_newsletter:
        success, msg = subscribe_workflow(email, user.id)
        if success:
            newsletter_msg = msg
        else:
            newsletter_msg = f"Account created, but newsletter subscription failed: {msg}"
    else:
        # Check if they were already subscribed anonymously
        subscriber = get_newsletter_subscriber_by_email(email)
        if subscriber:
            link_newsletter_subscriber_to_user(subscriber, user.id)

    # Send verification email
    send_verification_email(email, verification_token)

    return user, newsletter_msg
