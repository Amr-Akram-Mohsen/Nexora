import logging
from app.core.extensions import db
from app.domains.user.service import update_user_name, update_user_password
logger = logging.getLogger(__name__)
def update_profile_name_workflow(user, new_name: str) -> None:
    update_user_name(user, new_name)
    db.session.commit()
    logger.info('[AUTH] User %s updated display name', user.id)
def update_profile_password_workflow(user, new_password: str) -> None:
    update_user_password(user, new_password)
    db.session.commit()
    logger.info('[AUTH] User %s updated password', user.id)
def delete_account_workflow(user) -> None:
    from app.domains.user.service.command import delete_user
    delete_user(user)
    db.session.commit()
    logger.info('[AUTH] User %s deleted their account', user.id)