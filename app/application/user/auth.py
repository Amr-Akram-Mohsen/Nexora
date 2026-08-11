import logging
import random
import secrets
from flask import current_app
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from app.core.extensions import cache, db
from app.domains.user.models import User
from app.domains.user.service import get_active_user_by_email, get_user_by_email, get_user_by_id, create_user, mark_user_verified, record_login, reset_password, set_verification_sent, get_newsletter_subscriber_by_email, link_newsletter_subscriber_to_user
from app.application.interaction.newsletter import subscribe_workflow
from app.application.user.email_service import send_password_reset_email, send_verification_email
logger = logging.getLogger(__name__)
def authenticate_user(email: str, password: str):
    user = get_active_user_by_email(email)
    if user and user.check_password(password):
        return user
    return None
def check_login_lockout(email: str) -> tuple[bool, int]:
    lockout_key = f'login_lockout:{email}'
    locked = cache.get(lockout_key)
    if locked:
        return (True, 15)
    return (False, 0)
def record_failed_login(email: str) -> int:
    attempts_key = f'login_attempts:{email}'
    lockout_key = f'login_lockout:{email}'
    window = 900
    attempts = (cache.get(attempts_key) or 0) + 1
    if attempts >= 5:
        cache.set(lockout_key, True, timeout=window)
        cache.delete(attempts_key)
        return 0
    else:
        cache.set(attempts_key, attempts, timeout=window)
        return attempts
def clear_failed_logins(email: str) -> None:
    cache.delete(f'login_attempts:{email}')
    cache.delete(f'login_lockout:{email}')
def handle_successful_login(user) -> None:
    record_login(user)
    db.session.commit()
def handle_google_oauth_login(user_info: dict):
    email = user_info.get('email')
    user = get_user_by_email(email)
    if user:
        if not user.google_id:
            user.google_id = user_info.get('sub')
            user.provider = 'google'
            if not user.is_verified:
                mark_user_verified(user)
            else:
                db.session.commit()
    else:
        user = User(email=email, name=user_info.get('name'), provider='google', google_id=user_info.get('sub'), is_verified=True)
        user.set_password(secrets.token_urlsafe(24))
        db.session.add(user)
        db.session.commit()
        mark_user_verified(user)
    handle_successful_login(user)
    return user
OTP_TIMEOUT = 900
def generate_otp(email: str, intent: str) -> str:
    code = f'{random.randint(100000, 999999)}'
    key = f'otp:{intent}:{email}'
    cache.set(key, code, timeout=OTP_TIMEOUT)
    logger.info('[AUTH] Generated %s OTP for %s', intent, email)
    return code
def verify_otp(email: str, intent: str, code: str) -> bool:
    if not code:
        return False
    key = f'otp:{intent}:{email}'
    stored = cache.get(key)
    if stored and stored == str(code).strip():
        cache.delete(key)
        logger.info('[AUTH] Successfully verified %s OTP for %s', intent, email)
        return True
    logger.warning('[AUTH] Failed to verify %s OTP for %s', intent, email)
    return False
def request_password_reset(email: str) -> bool:
    user = get_user_by_email(email)
    if user and user.provider != 'google':
        code = generate_otp(email, 'reset')
        sent = send_password_reset_email(email, code)
        if sent:
            logger.info('[AUTH] Password reset email sent to %s (user_id=%s)', email, user.id)
        else:
            logger.warning('[AUTH] Password reset email FAILED for %s (user_id=%s)', email, user.id)
    db.session.commit()
    return True
def reset_user_password(email: str, new_password: str) -> tuple[bool, str]:
    user = get_user_by_email(email)
    if not user:
        return (False, 'Invalid account.')
    reset_password(user, new_password)
    db.session.commit()
    logger.info('[AUTH] Password successfully reset for user_id=%s', user.id)
    return (True, 'Password updated successfully!')
def register_user_workflow(name: str, email: str, password: str, wants_newsletter: bool=False):
    logger.info('[AUTH] Registration workflow start for email: %s', email)
    if get_user_by_email(email):
        logger.info('[AUTH] Registration aborted: account with email %s already exists.', email)
        return (None, 'An account with this email already exists.', False)
    user = create_user(name, email, password)
    logger.info('[AUTH] User created in DB with user_id=%s for email: %s', user.id, email)
    newsletter_msg = None
    if wants_newsletter:
        logger.info('[AUTH] User opted into newsletter for user_id=%s', user.id)
        success, msg = subscribe_workflow(email, user.id)
        newsletter_msg = msg if success else f'Account created, but newsletter signup failed: {msg}'
    else:
        subscriber = get_newsletter_subscriber_by_email(email)
        if subscriber:
            logger.info('[AUTH] Linking existing newsletter subscription to user_id=%s', user.id)
            link_newsletter_subscriber_to_user(subscriber, user.id)
    code = generate_otp(email, 'register')
    sent = send_verification_email(email, code)
    if sent:
        set_verification_sent(user)
        logger.info('[AUTH] Verification email sent to %s (user_id=%s)', email, user.id)
    else:
        logger.warning('[AUTH] Verification email FAILED to send to %s (user_id=%s)', email, user.id)
    db.session.commit()
    return (user, newsletter_msg, sent)
_VERIFY_SALT = 'nexora-email-verify-v1'
_RESET_SALT = 'nexora-password-reset-v1'
VERIFY_MAX_AGE = 86400
RESET_MAX_AGE = 3600
def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.secret_key)
def generate_verification_token(user_id: int) -> str:
    token = _serializer().dumps(user_id, salt=_VERIFY_SALT)
    logger.info('[AUTH] Generated verification token for user_id=%s', user_id)
    return token
def validate_verification_token(token: str) -> tuple[int | None, str | None]:
    try:
        user_id = _serializer().loads(token, salt=_VERIFY_SALT, max_age=VERIFY_MAX_AGE)
        return (int(user_id), None)
    except SignatureExpired:
        logger.info('[AUTH] Verification token expired')
        return (None, 'expired')
    except BadSignature:
        logger.warning('[AUTH] Invalid/tampered verification token')
        return (None, 'invalid')
def generate_reset_token(user) -> str:
    payload = {'id': user.id, 'pc': user.password_changed_at.timestamp() if user.password_changed_at else 0}
    token = _serializer().dumps(payload, salt=_RESET_SALT)
    logger.debug('[AUTH] Generated reset token for user_id=%s', user.id)
    return token
def validate_reset_token(token: str) -> tuple[dict | None, str | None]:
    try:
        payload = _serializer().loads(token, salt=_RESET_SALT, max_age=RESET_MAX_AGE)
        return (payload, None)
    except SignatureExpired:
        logger.info('[AUTH] Password reset token expired')
        return (None, 'expired')
    except BadSignature:
        logger.warning('[AUTH] Invalid/tampered password reset token')
        return (None, 'invalid')
def verify_user_email(email: str, code: str):
    if not verify_otp(email, 'register', code):
        return (None, 'invalid')
    user = get_user_by_email(email)
    if not user:
        logger.warning('[AUTH] OTP verified for %s but user not found', email)
        return (None, 'invalid')
    if user.is_verified:
        logger.info('[AUTH] User %s already verified, skipping re-verification', user.email)
        return (user, None)
    mark_user_verified(user)
    db.session.commit()
    logger.info('[AUTH] Email verified for user_id=%s (%s)', user.id, user.email)
    return (user, None)
def resend_verification_email_workflow(email: str) -> bool:
    user = get_user_by_email(email)
    if not user or user.is_verified:
        return True
    code = generate_otp(email, 'register')
    sent = send_verification_email(email, code)
    if sent:
        set_verification_sent(user)
        logger.info('[AUTH] Resent verification email to %s (user_id=%s)', email, user.id)
    else:
        logger.warning('[AUTH] Resend verification email FAILED for %s (user_id=%s)', email, user.id)
    db.session.commit()
    return True