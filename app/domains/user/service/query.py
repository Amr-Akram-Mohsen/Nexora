from app.domains.user.models import User


def get_users(rows_count=10):
    query = User.query.order_by(User.created_at.desc())

    if rows_count:
        query = query.limit(rows_count)

    return query.all()
