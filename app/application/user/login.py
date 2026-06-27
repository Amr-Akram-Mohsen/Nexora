from app.domains.user.service import get_active_user_by_email
from app.core.extensions import cache


def authenticate_user(email: str, password: str):
    """
    Authenticates a user and returns the user object if credentials are valid.
    Returns None on failure.
    """
    user = get_active_user_by_email(email)
    if user and user.check_password(password):
        return user
    return None


def check_login_lockout(email: str) -> tuple[bool, int]:
    """
    Checks if an email is currently locked out due to too many failed login attempts.
    Returns (is_locked_out, minutes_remaining).
    """
    lockout_key = f"login_lockout:{email}"
    locked = cache.get(lockout_key)
    if locked:
        # Return a conservative estimate; cache TTL not directly accessible
        return True, 15
    return False, 0


def record_failed_login(email: str) -> int:
    """
    Records a failed login attempt for the given email.
    Locks the account for 15 minutes after 5 consecutive failures.
    Returns the current attempt count (0 once locked).
    """
    attempts_key = f"login_attempts:{email}"
    lockout_key  = f"login_lockout:{email}"
    window       = 900  # 15 minutes in seconds

    attempts = (cache.get(attempts_key) or 0) + 1

    if attempts >= 5:
        cache.set(lockout_key, True, timeout=window)
        cache.delete(attempts_key)
        return 0
    else:
        cache.set(attempts_key, attempts, timeout=window)
        return attempts


def clear_failed_logins(email: str) -> None:
    """
    Clears all failed login state for an email after a successful login.
    """
    cache.delete(f"login_attempts:{email}")
    cache.delete(f"login_lockout:{email}")


def handle_successful_login(user) -> None:
    """
    Handles side effects of a successful login.
    """
    from app.core.extensions import db
    from app.domains.user.service import record_login
    record_login(user)
    db.session.commit()


def handle_google_oauth_login(user_info: dict):
    """
    Handles Google OAuth login workflow.
    Creates or updates the user and returns the user object.
    """
    from app.core.extensions import db
    from app.domains.user.service import get_user_by_email, create_user, mark_user_verified
    from app.domains.user.models import User
    import secrets

    email = user_info.get('email')
    user = get_user_by_email(email)
    
    if user:
        if not user.google_id:
            user.google_id  = user_info.get('sub')
            user.provider   = 'google'
            if not user.is_verified:
                mark_user_verified(user)
            else:
                db.session.commit()
    else:
        user = User(
            email=email,
            name=user_info.get('name'),
            provider='google',
            google_id=user_info.get('sub'),
            is_verified=True,
        )
        user.set_password(secrets.token_urlsafe(24))
        db.session.add(user)
        db.session.commit()
        mark_user_verified(user)
    
    handle_successful_login(user)
    return user
