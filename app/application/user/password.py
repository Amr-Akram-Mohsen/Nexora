import logging
from app.domains.user.service import get_user_by_email, get_user_by_id, reset_password
from app.application.user.tokens import generate_reset_token, validate_reset_token
from app.application.user.email_service import send_password_reset_email

logger = logging.getLogger(__name__)


def request_password_reset(email: str) -> bool:
    """
    Initiates a password reset for the given email.
    - Google-linked accounts cannot use password reset (no local password).
    - Always returns True to prevent email enumeration.
    """
    user = get_user_by_email(email)
    if user and user.provider != 'google':
        token = generate_reset_token(user)
        sent  = send_password_reset_email(email, token)
        if sent:
            logger.info("[AUTH] Password reset email sent to %s (user_id=%s)", email, user.id)
        else:
            logger.warning("[AUTH] Password reset email FAILED for %s (user_id=%s)", email, user.id)
    return True


def reset_user_password(token: str, new_password: str) -> tuple[bool, str]:
    """
    Validates a signed reset token and applies the new password.

    Security: the token embeds password_changed_at, so it is automatically
    invalidated if the user has changed their password since the link was sent.

    Returns (True, success_message) or (False, error_message).
    """
    payload, error = validate_reset_token(token)

    if error == 'expired':
        return False, "This password reset link has expired. Please request a new one."
    if error == 'invalid':
        return False, "This password reset link is invalid."

    user = get_user_by_id(payload['id'])
    if not user:
        logger.warning("[AUTH] Reset token decoded user_id=%s but user not found", payload.get('id'))
        return False, "Invalid password reset link."

    # Invalidate if password has already been changed since this link was generated
    if str(user.password_changed_at) != payload['pc']:
        logger.info("[AUTH] Reset token superseded for user_id=%s (password already changed)", user.id)
        return False, "This password reset link has already been used."

    reset_password(user, new_password)
    logger.info("[AUTH] Password successfully reset for user_id=%s", user.id)
    return True, "Password updated successfully!"
