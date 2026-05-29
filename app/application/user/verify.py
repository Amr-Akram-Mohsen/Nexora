import logging
from app.domains.user.service import (
    get_user_by_email,
    get_user_by_id,
    mark_user_verified,
    set_verification_sent,
)
from app.application.user.tokens import (
    generate_verification_token,
    validate_verification_token,
)
from app.application.user.email_service import send_verification_email

logger = logging.getLogger(__name__)


def verify_user_email(token: str):
    """
    Validates a signed verification token and marks the user as verified.

    Returns: (user, None) on success.
             (None, 'expired') if the 24-hour window has passed.
             (None, 'invalid') if the token is malformed or tampered.
    """
    user_id, error = validate_verification_token(token)
    if error:
        return None, error

    user = get_user_by_id(user_id)
    if not user:
        logger.warning("[AUTH] Verification token decoded user_id=%s but user not found", user_id)
        return None, 'invalid'

    if user.is_verified:
        # Already verified — treat as success so they can log in
        logger.info("[AUTH] User %s already verified, skipping re-verification", user.email)
        return user, None

    mark_user_verified(user)
    logger.info("[AUTH] Email verified for user_id=%s (%s)", user_id, user.email)
    return user, None


def resend_verification_email_workflow(email: str) -> bool:
    """
    Resends a verification email if the account exists and is still unverified.
    Always returns True to prevent email enumeration.
    """
    user = get_user_by_email(email)
    if not user or user.is_verified:
        return True  # Silent no-op for enumeration safety

    token = generate_verification_token(user.id)
    sent  = send_verification_email(email, token)

    if sent:
        set_verification_sent(user)
        logger.info("[AUTH] Resent verification email to %s (user_id=%s)", email, user.id)
    else:
        logger.warning("[AUTH] Resend verification email FAILED for %s (user_id=%s)", email, user.id)

    return True
