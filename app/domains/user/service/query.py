from app.domains.user.models import User, NewsletterSubscriber
from app.core.extensions import db
from sqlalchemy import or_


def count_users() -> int:
    return db.session.query(User.id).count()


def get_users(search=None, role=None, rows_count=10):
    query = User.query.order_by(User.id.desc())
    if search and search.strip():
        query = query.filter(
            or_(User.name.ilike(f'%{search}%'), User.email.ilike(f'%{search}%'))
        )
    if role:
        if role.lower() == 'admin':
            query = query.filter(User.is_admin == True)
        elif role.lower() == 'user':
            query = query.filter(User.is_admin == False)
    if rows_count:
        query = query.limit(rows_count)
    return query.all()


def get_user_by_id(user_id: int):
    """Returns a User by primary key, or None."""
    return db.session.get(User, user_id)


def get_user_by_email(email: str):
    return User.query.filter_by(email=email).first()


def get_active_user_by_email(email: str):
    return User.query.filter(User.email == email, User.is_active == True).first()


def get_newsletter_subscriber_by_email(email: str):
    """Returns the NewsletterSubscriber for a given email, or None."""
    return NewsletterSubscriber.query.filter_by(email=email).first()
