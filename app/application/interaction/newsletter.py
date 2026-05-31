import logging

from sqlalchemy.exc import IntegrityError

from app.application.user.email_service import send_confirmation_email
from app.core.extensions import db
from app.domains.user.service import (
    confirm_newsletter_subscriber,
    create_newsletter_subscriber,
    get_newsletter_subscriber_by_email,
    link_newsletter_subscriber_to_user,
    unsubscribe_newsletter_subscriber,
)

logger = logging.getLogger(__name__)


def _normalize_email(email):
    return (email or "").strip().lower()


def _send_confirmation(subscriber):
    sent = send_confirmation_email(
        subscriber.email,
        subscriber.confirmation_token,
        subscriber.unsubscribe_token,
    )
    if not sent:
        logger.warning(
            "Newsletter confirmation email was not sent",
            extra={"subscriber_id": subscriber.id, "email": subscriber.email},
        )
    return sent


def subscribe_workflow(email, user_id=None):
    """
    Handles newsletter subscription as an idempotent double opt-in workflow.
    """
    from app.shared.validators import validate_email

    email = _normalize_email(email)
    if not email:
        return False, "Email is required."
    if not validate_email(email):
        return False, "Invalid email address format."

    subscriber = get_newsletter_subscriber_by_email(email)

    if subscriber:
        if user_id and subscriber.user_id != user_id:
            link_newsletter_subscriber_to_user(subscriber, user_id)

        if subscriber.is_active:
            return True, "You are already subscribed."

        if subscriber.unsubscribed_at is None and not subscriber.is_confirmed:
            if not subscriber.confirmation_token or not subscriber.unsubscribe_token:
                subscriber.generate_tokens()
                db.session.commit()
            _send_confirmation(subscriber)
            return True, "Check your email to confirm your subscription."

        subscriber.unsubscribed_at = None
        subscriber.is_confirmed = False
        subscriber.generate_tokens()
        db.session.commit()
    else:
        try:
            subscriber = create_newsletter_subscriber(email, user_id)
        except IntegrityError:
            db.session.rollback()
            subscriber = get_newsletter_subscriber_by_email(email)
            if not subscriber:
                logger.exception("Newsletter subscriber create race failed")
                return False, "We could not start your subscription. Please try again."
            if subscriber.is_active:
                return True, "You are already subscribed."
            if subscriber.unsubscribed_at is None and not subscriber.is_confirmed:
                if not subscriber.confirmation_token or not subscriber.unsubscribe_token:
                    subscriber.generate_tokens()
                    db.session.commit()
                _send_confirmation(subscriber)
                return True, "Check your email to confirm your subscription."
            subscriber.unsubscribed_at = None
            subscriber.is_confirmed = False
            subscriber.generate_tokens()
            db.session.commit()

    _send_confirmation(subscriber)
    return True, "Check your email to confirm your subscription."


def confirm_subscription_workflow(token):
    """
    Confirms a subscription using a token.
    """
    return confirm_newsletter_subscriber(token)


def unsubscribe_workflow(user=None, token=None):
    """
    Unsubscribes a user or token-linked subscriber.
    """
    if token:
        return unsubscribe_newsletter_subscriber(token=token)

    if user:
        subscriber = getattr(user, "newsletter_subscription", None)
        if not subscriber or subscriber.unsubscribed_at is not None:
            return False, "You are not subscribed."
        return unsubscribe_newsletter_subscriber(subscriber=subscriber)

    return False, "Invalid unsubscribe request."
