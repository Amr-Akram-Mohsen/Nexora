"""
app/application/user/tokens.py

Stateless signed tokens for email verification and password reset.
Uses itsdangerous URLSafeTimedSerializer with Flask's SECRET_KEY.
No tokens are stored in the database — validation is entirely stateless.
"""
import logging
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask import current_app

logger = logging.getLogger(__name__)

_VERIFY_SALT = 'nexora-email-verify-v1'
_RESET_SALT  = 'nexora-password-reset-v1'

VERIFY_MAX_AGE = 86400  # 24 hours
RESET_MAX_AGE  = 3600   # 1 hour


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.secret_key)


# ── Email Verification ─────────────────────────────────────────────────────────

def generate_verification_token(user_id: int) -> str:
    """Returns a signed, time-limited email verification token for a user ID."""
    token = _serializer().dumps(user_id, salt=_VERIFY_SALT)
    logger.info("[AUTH] Generated verification token for user_id=%s", user_id)
    return token


def validate_verification_token(token: str) -> tuple[int | None, str | None]:
    """
    Validates an email verification token.
    Returns (user_id, None) on success.
    Returns (None, 'expired') if the token has exceeded 24 hours.
    Returns (None, 'invalid') if the token is malformed or tampered.
    """
    try:
        user_id = _serializer().loads(token, salt=_VERIFY_SALT, max_age=VERIFY_MAX_AGE)
        return int(user_id), None
    except SignatureExpired:
        logger.info("[AUTH] Verification token expired")
        return None, 'expired'
    except BadSignature:
        logger.warning("[AUTH] Invalid/tampered verification token")
        return None, 'invalid'


# ── Password Reset ─────────────────────────────────────────────────────────────

def generate_reset_token(user) -> str:
    """
    Returns a signed, time-limited password reset token.
    Embeds user.password_changed_at so the token is automatically invalidated
    if the password is changed before the link is used.
    """
    payload = {
        'id':  user.id,
        'pc':  user.password_changed_at.timestamp() if user.password_changed_at else 0,
    }
    token = _serializer().dumps(payload, salt=_RESET_SALT)
    logger.debug("[AUTH] Generated reset token for user_id=%s", user.id)
    return token


def validate_reset_token(token: str) -> tuple[dict | None, str | None]:
    """
    Validates a password reset token.
    Returns (payload_dict, None) on success — payload has keys 'id' and 'pc'.
    Returns (None, 'expired') if the token has exceeded 1 hour.
    Returns (None, 'invalid') if the token is malformed or tampered.
    """
    try:
        payload = _serializer().loads(token, salt=_RESET_SALT, max_age=RESET_MAX_AGE)
        return payload, None
    except SignatureExpired:
        logger.info("[AUTH] Password reset token expired")
        return None, 'expired'
    except BadSignature:
        logger.warning("[AUTH] Invalid/tampered password reset token")
        return None, 'invalid'
