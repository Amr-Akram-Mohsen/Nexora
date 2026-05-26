from app.domains.user.service import get_active_user_by_email
from app.core.extensions import cache

def authenticate_user(email, password):
    """
    Authenticates a user and returns the user object if successful.
    """
    user = get_active_user_by_email(email)
    if user and user.check_password(password):
        return user
    return None

def check_login_lockout(email: str) -> tuple[bool, int]:
    """
    Checks if an email is locked out due to too many failed login attempts.
    Returns (is_locked_out, minutes_remaining).
    """
    lockout_key = f"login_lockout:{email}"
    if cache.get(lockout_key):
        return True, 15
    return False, 0

def record_failed_login(email: str):
    """
    Records a failed login attempt. After 5 attempts, locks out for 15 minutes.
    """
    attempts_key = f"login_attempts:{email}"
    lockout_key = f"login_lockout:{email}"
    
    attempts = cache.get(attempts_key) or 0
    attempts += 1
    
    if attempts >= 5:
        cache.set(lockout_key, True, timeout=900)  # 15 minutes lockout
        cache.delete(attempts_key)
    else:
        cache.set(attempts_key, attempts, timeout=900)  # 15 minutes window

def clear_failed_logins(email: str):
    """
    Clears failed login attempts after a successful login.
    """
    attempts_key = f"login_attempts:{email}"
    lockout_key = f"login_lockout:{email}"
    cache.delete(attempts_key)
    cache.delete(lockout_key)
