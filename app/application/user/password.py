import logging
from app.domains.user.service import get_user_by_email, get_user_by_id, reset_password
from app.application.user.otp import generate_otp
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
        code = generate_otp(email, "reset")
        sent  = send_password_reset_email(email, code)
        if sent:
            logger.info("[AUTH] Password reset email sent to %s (user_id=%s)", email, user.id)
        else:
            logger.warning("[AUTH] Password reset email FAILED for %s (user_id=%s)", email, user.id)

    from app.core.extensions import db
    db.session.commit()
    return True



def reset_user_password(email: str, new_password: str) -> tuple[bool, str]:
    """
    Applies the new password for the verified email.
    """
    user = get_user_by_email(email)
    if not user:
        return False, "Invalid account."

    reset_password(user, new_password)
    from app.core.extensions import db
    db.session.commit()
    logger.info("[AUTH] Password successfully reset for user_id=%s", user.id)
    return True, "Password updated successfully!"

