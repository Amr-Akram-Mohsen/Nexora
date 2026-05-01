from app.domains.user.models import User
from app.core.extensions import db


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

import secrets
from app.domains.user.models import NewsletterSubscriber

def create_user(name, email, password):
    verification_token = secrets.token_urlsafe(32)
    user = User(
        email=email,
        name=name,
        is_verified=False,
        verification_token=verification_token,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user, verification_token

def get_newsletter_subscriber_by_email(email):
    return NewsletterSubscriber.query.filter_by(email=email).first()

def create_newsletter_subscriber(email, user_id=None):
    subscriber = NewsletterSubscriber(email=email, user_id=user_id)
    subscriber.generate_tokens()
    db.session.add(subscriber)
    db.session.commit()
    return subscriber

def link_newsletter_subscriber_to_user(subscriber, user_id):
    subscriber.user_id = user_id
    db.session.commit()
    return subscriber

def verify_user(user):
    user.is_verified = True
    user.verification_token = None
    db.session.commit()
    return user

def set_reset_token(user, token, expires_at):
    user.reset_token = token
    user.reset_token_expires_at = expires_at
    db.session.commit()
    return user

def reset_password(user, new_password):
    user.set_password(new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.session.commit()
    return user

def update_user_name(user, name):
    user.name = name[:120]
    db.session.commit()
    return user

def update_user_password(user, new_password):
    user.set_password(new_password)
    db.session.commit()
    return user

def confirm_newsletter_subscriber(token):
    subscriber = NewsletterSubscriber.query.filter_by(confirmation_token=token).first()
    if not subscriber:
        return False
    
    subscriber.is_confirmed = True
    subscriber.confirmation_token = None
    subscriber.unsubscribed_at = None
    db.session.commit()
    return True

def unsubscribe_newsletter_subscriber(token=None, subscriber=None):
    if token:
        subscriber = NewsletterSubscriber.query.filter_by(unsubscribe_token=token).first()
    
    if not subscriber:
        return False
    
    from datetime import datetime, timezone
    subscriber.unsubscribed_at = datetime.now(timezone.utc)
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
        user_agent=user_agent
    )
    db.session.add(msg)
    db.session.commit()
    return msg
