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

    subscriber = get_newsletter_subscriber_by_email(email)

    if subscriber:
        if user_id:
            link_newsletter_subscriber_to_user(subscriber, user_id)

        if subscriber.is_active:
            return False, "You are already subscribed."

        subscriber.unsubscribed_at = None
        if not subscriber.is_confirmed:
            subscriber.generate_tokens()
    else:
        subscriber = create_newsletter_subscriber(email, user_id)

    # Note: DB commit is handled in domain service or here? 
    # The domain service create_newsletter_subscriber already commits.
    
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
