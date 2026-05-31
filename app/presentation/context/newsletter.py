from flask_login import current_user
from app.domains.user.service import get_newsletter_subscriber_by_email


def _state_for_subscriber(subscriber):
    if not subscriber:
        return "anonymous"
    if subscriber.is_active:
        return "subscribed"
    if subscriber.unsubscribed_at is None:
        return "pending"
    return "unsubscribed"


def get_newsletter_context(subscriber=None, email=None):
    is_authenticated = current_user.is_authenticated

    if subscriber is None:
        if is_authenticated:
            subscriber = current_user.newsletter_subscription
        elif email:
            subscriber = get_newsletter_subscriber_by_email(email.strip().lower())

    status = _state_for_subscriber(subscriber)
    is_pending = status == "pending"
    is_subscribed = status == "subscribed"

    newsletter_email = subscriber.email if subscriber else (
        current_user.email if is_authenticated else None
    )

    return {
        'is_authenticated': is_authenticated,
        'is_subscribed': is_subscribed,
        'is_pending': is_pending,
        'newsletter_status': status,
        'newsletter_email': newsletter_email,
    }
