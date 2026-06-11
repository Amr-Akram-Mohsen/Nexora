from datetime import datetime, timezone
from app.domains.user.models import User, NewsletterSubscriber
from app.core.extensions import db


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── User Lifecycle ─────────────────────────────────────────────────────────────

def create_user(name: str, email: str, password: str, session=None) -> 'User':
    """
    Creates and persists a new local user.
    Returns the User instance. Token generation is handled by the application layer.
    """
    if session is None:
        session = db.session
    user = User(
        email=email,
        name=name,
        is_verified=False,
    )
    user.set_password(password)
    session.add(user)
    session.flush()
    return user


def deactivate_user(id: int, session=None) -> bool:
    if session is None:
        session = db.session
    user = session.get(User, id)
    if not user:
        return False
    user.is_active = False
    session.flush()
    return True


def activate_user(id: int, session=None) -> bool:
    if session is None:
        session = db.session
    user = session.get(User, id)
    if not user:
        return False
    user.is_active = True
    session.flush()
    return True


# ── Auth Event Tracking ────────────────────────────────────────────────────────

def mark_user_verified(user, session=None) -> 'User':
    """Sets is_verified=True and records verified_at timestamp."""
    if session is None:
        session = db.session
    user.is_verified  = True
    user.verified_at  = _now()
    session.flush()
    return user


def set_verification_sent(user, session=None) -> 'User':
    """Records that a verification email was just sent."""
    if session is None:
        session = db.session
    user.verification_sent_at = _now()
    session.flush()
    return user


def record_login(user, session=None) -> 'User':
    """Records a successful login timestamp."""
    if session is None:
        session = db.session
    user.last_login_at = _now()
    session.flush()
    return user


def mark_password_changed(user, session=None) -> 'User':
    """Records that the user's password was just changed or reset."""
    if session is None:
        session = db.session
    user.password_changed_at = _now()
    session.flush()
    return user


# ── Password ───────────────────────────────────────────────────────────────────

def reset_password(user, new_password: str, session=None) -> 'User':
    """Resets the user's password and records the change timestamp."""
    if session is None:
        session = db.session
    user.set_password(new_password)
    user.password_changed_at = _now()
    session.flush()
    return user


def update_user_name(user, name: str, session=None) -> 'User':
    if session is None:
        session = db.session
    user.name = name[:120]
    session.flush()
    return user


def update_user_password(user, new_password: str, session=None) -> 'User':
    """Updates the user's password and records the change timestamp."""
    if session is None:
        session = db.session
    user.set_password(new_password)
    user.password_changed_at = _now()
    session.flush()
    return user


# ── Newsletter ─────────────────────────────────────────────────────────────────

def create_newsletter_subscriber(email: str, user_id=None, session=None) -> NewsletterSubscriber:
    if session is None:
        session = db.session
    subscriber = NewsletterSubscriber(email=email, user_id=user_id)
    subscriber.generate_tokens()
    session.add(subscriber)
    session.flush()
    return subscriber


def link_newsletter_subscriber_to_user(subscriber, user_id: int, session=None) -> NewsletterSubscriber:
    if session is None:
        session = db.session
    subscriber.user_id = user_id
    session.flush()
    return subscriber


def confirm_newsletter_subscriber(token: str, session=None) -> bool:
    if session is None:
        session = db.session
    subscriber = session.query(NewsletterSubscriber).filter_by(confirmation_token=token).first()
    if not subscriber:
        return False
    subscriber.is_confirmed      = True
    subscriber.confirmation_token = None
    subscriber.unsubscribed_at   = None
    if not subscriber.unsubscribe_token:
        subscriber.generate_tokens()
        subscriber.confirmation_token = None
    session.flush()
    return True


def unsubscribe_newsletter_subscriber(token=None, subscriber=None, session=None) -> bool:
    if session is None:
        session = db.session
    if token:
        subscriber = session.query(NewsletterSubscriber).filter_by(unsubscribe_token=token).first()
    if not subscriber:
        return False
    subscriber.unsubscribed_at = _now()
    subscriber.is_confirmed = False
    subscriber.confirmation_token = None
    session.flush()
    return True


def create_contact_message(name, email, subject, message, ip_address, user_agent, session=None):
    from app.domains.user.models import ContactMessage
    if session is None:
        session = db.session
    msg = ContactMessage(
        name=name,
        email=email,
        subject=subject,
        message=message,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(msg)
    session.flush()
    return msg
