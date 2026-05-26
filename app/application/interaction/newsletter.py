from app.domains.user.service import (
    get_newsletter_subscriber_by_email,
    create_newsletter_subscriber,
    link_newsletter_subscriber_to_user,
    confirm_newsletter_subscriber,
    unsubscribe_newsletter_subscriber
)
from app.application.user.email_service import send_confirmation_email

def subscribe_workflow(email, user_id=None):
    """
    Handles newsletter subscription.
    """
    if not email:
        return False, "Email is required."

    from app.shared.validators import validate_email
    email = email.strip().lower()
    if not validate_email(email):
        return False, "Invalid email address format."

    subscriber = get_newsletter_subscriber_by_email(email)

    from app.core.extensions import db

    if subscriber:
        if user_id:
            link_newsletter_subscriber_to_user(subscriber, user_id)

        if subscriber.is_active:
            return False, "You are already subscribed."

        # Re-subscribe: reset verification tokens for double opt-in
        subscriber.unsubscribed_at = None
        subscriber.is_confirmed = False
        subscriber.generate_tokens()
        db.session.commit()
    else:
        subscriber = create_newsletter_subscriber(email, user_id)

    send_confirmation_email(
        subscriber.email,
        subscriber.confirmation_token,
        subscriber.unsubscribe_token
    )

    return True, "Check your email to confirm subscription 📬"

def confirm_subscription_workflow(token):
    """
    Confirms a subscription using a token.
    """
    return confirm_newsletter_subscriber(token)

def unsubscribe_workflow(user=None, token=None):
    """
    Unsubscribes a user.
    """
    if token:
        return unsubscribe_newsletter_subscriber(token=token)
    elif user:
        subscriber = getattr(user, "newsletter_subscription", None)
        if not subscriber or not subscriber.is_active:
            return False, "You are not subscribed."
        return unsubscribe_newsletter_subscriber(subscriber=subscriber)
    
    return False, "Invalid unsubscribe request."
