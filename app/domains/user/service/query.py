from app.domains.user.models import User
from app.core.extensions import db

def count_users():
    return db.session.query(User.id).count()

from sqlalchemy import or_

def get_users(search=None, role=None, rows_count=10):
    query = User.query.order_by(User.created_at.desc())

    if search and search.strip():
        query = query.filter(or_(User.name.ilike(f'%{search}%'), User.email.ilike(f'%{search}%')))
    
    if role:
        if role.lower() == 'admin':
            query = query.filter(User.is_admin == True)
        elif role.lower() == 'user':
            query = query.filter(User.is_admin == False)

    if rows_count:
        query = query.limit(rows_count)

    return query.all()
def get_user_by_email(email):
    return User.query.filter_by(email=email).first()

def get_active_user_by_email(email):
    return User.query.filter(User.email == email, User.is_active == True).first()

def get_user_by_verification_token(token):
    return User.query.filter_by(verification_token=token).first()

def get_user_by_reset_token(token):
    return User.query.filter_by(reset_token=token).first()
