from app.core.extensions import db
from app.domains.user.service import deactivate_user as domain_deactivate_user, activate_user as domain_activate_user
from app.domains.user.service.admin import toggle_admin_user as domain_toggle_admin_user

def deactivate_user_workflow(user_id):
    success = domain_deactivate_user(user_id)
    if success:
        db.session.commit()
    return success

def activate_user_workflow(user_id):
    success = domain_activate_user(user_id)
    if success:
        db.session.commit()
    return success

def toggle_admin_user_workflow(user_id):
    user = domain_toggle_admin_user(user_id)
    if user:
        db.session.commit()
    return user

def delete_subscriber_workflow(sub_id):
    from app.domains.user.models import NewsletterSubscriber
    sub = db.session.get(NewsletterSubscriber, sub_id)
    if not sub:
        return False
    db.session.delete(sub)
    db.session.commit()
    return True
