import secrets
from app.domains.user.service import get_user_by_verification_token, verify_user, get_user_by_email
from app.application.user.email_service import send_verification_email
from app.shared.validators import hash_token
from app.core.extensions import db

def verify_user_email(token):
    """
    Verifies a user's email using a token.
    """
    user = get_user_by_verification_token(token)
    if not user:
        return None
    
    return verify_user(user)

def resend_verification_email_workflow(email):
    """
    Resends a verification email to the user if they are not verified.
    """
    user = get_user_by_email(email)
    if user and not user.is_verified:
        token = secrets.token_urlsafe(32)
        user.verification_token = hash_token(token)
        db.session.commit()
        send_verification_email(email, token)
    return True
