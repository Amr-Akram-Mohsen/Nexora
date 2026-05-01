from flask_login import current_user

def get_newsletter_context():
    is_authenticated = current_user.is_authenticated

    subscriber = (
        current_user.newsletter_subscription
        if is_authenticated else None
    )

    is_pending = (
        subscriber
        and not subscriber.is_confirmed
        and subscriber.unsubscribed_at is None
    )

    is_subscribed = (subscriber and subscriber.is_active)

    return {
        'is_authenticated': is_authenticated,
        'is_subscribed': is_subscribed,
        'is_pending': is_pending
    }
