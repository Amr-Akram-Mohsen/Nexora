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

