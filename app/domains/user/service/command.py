from datetime import datetime, timezone
from app.domains.user.models import User, NewsletterSubscriber
from app.core.extensions import db
def _now() -> datetime:
    return datetime.now(timezone.utc)
def create_user(name: str, email: str, password: str) -> 'User':
    user = User(email=email, name=name, is_verified=False)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    return user
def deactivate_user(id: int) -> bool:
    user = db.session.get(User, id)
    if not user:
        return False
    user.is_active = False
    db.session.flush()
    return True
def delete_user(user) -> bool:
    db.session.delete(user)
    db.session.flush()
    return True
def activate_user(id: int) -> bool:
    user = db.session.get(User, id)
    if not user:
        return False
    user.is_active = True
    db.session.flush()
    return True
def mark_user_verified(user) -> 'User':
    user.is_verified = True
    user.verified_at = _now()
    db.session.flush()
    return user
def set_verification_sent(user) -> 'User':
    user.verification_sent_at = _now()
    db.session.flush()
    return user
def record_login(user) -> 'User':
    user.last_login_at = _now()
    db.session.flush()
    return user
def mark_password_changed(user) -> 'User':
    user.password_changed_at = _now()
    db.session.flush()
    return user
def reset_password(user, new_password: str) -> 'User':
    user.set_password(new_password)
    user.password_changed_at = _now()
    db.session.flush()
    return user
def update_user_name(user, name: str) -> 'User':
    user.name = name[:120]
    db.session.flush()
    return user
def update_user_password(user, new_password: str) -> 'User':
    user.set_password(new_password)
    user.password_changed_at = _now()
    db.session.flush()
    return user
def create_newsletter_subscriber(email: str, user_id=None) -> NewsletterSubscriber:
    subscriber = NewsletterSubscriber(email=email, user_id=user_id)
    subscriber.generate_tokens()
    db.session.add(subscriber)
    db.session.flush()
    return subscriber
def link_newsletter_subscriber_to_user(subscriber, user_id: int) -> NewsletterSubscriber:
    subscriber.user_id = user_id
    db.session.flush()
    return subscriber
def confirm_newsletter_subscriber(token: str) -> bool:
    subscriber = db.session.query(NewsletterSubscriber).filter_by(confirmation_token=token).first()
    if not subscriber:
        return False
    subscriber.is_confirmed = True
    subscriber.confirmation_token = None
    subscriber.unsubscribed_at = None
    if not subscriber.unsubscribe_token:
        subscriber.generate_tokens()
        subscriber.confirmation_token = None
    db.session.flush()
    return True
def unsubscribe_newsletter_subscriber(token=None, subscriber=None) -> bool:
    if token:
        subscriber = db.session.query(NewsletterSubscriber).filter_by(unsubscribe_token=token).first()
    if not subscriber:
        return False
    subscriber.unsubscribed_at = _now()
    subscriber.is_confirmed = False
    subscriber.confirmation_token = None
    db.session.flush()
    return True
def create_contact_message(name, email, subject, message, ip_address, user_agent):
    from app.domains.user.models import ContactMessage
    msg = ContactMessage(name=name, email=email, subject=subject, message=message, ip_address=ip_address, user_agent=user_agent)
    db.session.add(msg)
    db.session.flush()
    return msg