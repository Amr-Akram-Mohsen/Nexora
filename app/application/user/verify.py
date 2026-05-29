import secrets
from app.domains.user.service import (
    get_user_by_verification_token,
    verify_user,
    get_user_by_email,
    set_verification_token,
)
from app.application.user.email_service import send_verification_email


def verify_user_email(token: str):
    """
    Verifies a user's email using a token.
    Returns the verified User on success, or None if the token is invalid.
    """
    user = get_user_by_verification_token(token)
    if not user:
        return None
    return verify_user(user)


def resend_verification_email_workflow(email: str) -> bool:
    """
    Resends a verification email to the user if the account exists and is unverified.
    Always returns True to prevent email enumeration.
    """
    user = get_user_by_email(email)
    if user and not user.is_verified:
        token = secrets.token_urlsafe(32)
        set_verification_token(user, token)
        send_verification_email(email, token)
    return True
