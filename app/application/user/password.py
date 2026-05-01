import secrets
from datetime import datetime, timezone, timedelta
from app.domains.user.service import get_user_by_email, set_reset_token, get_user_by_reset_token, reset_password
from app.application.user.email_service import send_password_reset_email

def request_password_reset(email):
    """
    Handles a password reset request.
    """
    user = get_user_by_email(email)
    if user and user.provider != 'google':
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        set_reset_token(user, token, expires_at)
        send_password_reset_email(email, token)
    # Always return true to prevent email enumeration
    return True

def reset_user_password(token, new_password):
    """
    Handles the actual password reset.
    """
    user = get_user_by_reset_token(token)
    if not user or not user.reset_token_expires_at:
        return False, "Invalid or expired password reset link."

    now = datetime.now(timezone.utc)
    expires = user.reset_token_expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    
    if now > expires:
        return False, "This password reset link has expired."

    reset_password(user, new_password)
    return True, "Password updated successfully!"
