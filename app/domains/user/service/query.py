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
