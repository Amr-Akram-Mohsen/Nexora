from datetime import datetime, timezone
from app.domains.user.models import User, NewsletterSubscriber
from app.core.extensions import db


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── User Lifecycle ─────────────────────────────────────────────────────────────

def create_user(name: str, email: str, password: str) -> 'User':
    """
    Creates and persists a new local user.
    Returns the User instance. Token generation is handled by the application layer.
    """
    user = User(
        email=email,
        name=name,
        is_verified=False,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def deactivate_user(id: int) -> bool:
    user = db.session.get(User, id)
    if not user:
        return False
    user.is_active = False
    db.session.commit()
    return True


def activate_user(id: int) -> bool:
    user = db.session.get(User, id)
    if not user:
        return False
    user.is_active = True
    db.session.commit()
    return True


# ── Auth Event Tracking ────────────────────────────────────────────────────────

def mark_user_verified(user) -> 'User':
    """Sets is_verified=True and records verified_at timestamp."""
    user.is_verified  = True
    user.verified_at  = _now()
    db.session.commit()
    return user


def set_verification_sent(user) -> 'User':
    """Records that a verification email was just sent."""
    user.verification_sent_at = _now()
    db.session.commit()
    return user


def record_login(user) -> 'User':
    """Records a successful login timestamp."""
    user.last_login_at = _now()
    db.session.commit()
    return user


def mark_password_changed(user) -> 'User':
    """Records that the user's password was just changed or reset."""
    user.password_changed_at = _now()
    db.session.commit()
    return user


# ── Password ───────────────────────────────────────────────────────────────────

def reset_password(user, new_password: str) -> 'User':
    """Resets the user's password and records the change timestamp."""
    user.set_password(new_password)
    user.password_changed_at = _now()
    db.session.commit()
    return user


def update_user_name(user, name: str) -> 'User':
    user.name = name[:120]
    db.session.commit()
    return user


def update_user_password(user, new_password: str) -> 'User':
    """Updates the user's password and records the change timestamp."""
    user.set_password(new_password)
    user.password_changed_at = _now()
    db.session.commit()
    return user


# ── Newsletter ─────────────────────────────────────────────────────────────────

def create_newsletter_subscriber(email: str, user_id=None) -> NewsletterSubscriber:
    subscriber = NewsletterSubscriber(email=email, user_id=user_id)
    subscriber.generate_tokens()
    db.session.add(subscriber)
    db.session.commit()
    return subscriber


def link_newsletter_subscriber_to_user(subscriber, user_id: int) -> NewsletterSubscriber:
    subscriber.user_id = user_id
    db.session.commit()
    return subscriber


def confirm_newsletter_subscriber(token: str) -> bool:
    subscriber = NewsletterSubscriber.query.filter_by(confirmation_token=token).first()
    if not subscriber:
        return False
    subscriber.is_confirmed      = True
    subscriber.confirmation_token = None
    subscriber.unsubscribed_at   = None
    db.session.commit()
    return True


def unsubscribe_newsletter_subscriber(token=None, subscriber=None) -> bool:
    if token:
        subscriber = NewsletterSubscriber.query.filter_by(unsubscribe_token=token).first()
    if not subscriber:
        return False
    subscriber.unsubscribed_at = _now()
    db.session.commit()
    return True


def create_contact_message(name, email, subject, message, ip_address, user_agent):
    from app.domains.user.models import ContactMessage
    msg = ContactMessage(
        name=name,
        email=email,
        subject=subject,
        message=message,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.session.add(msg)
    db.session.commit()
    return msg
