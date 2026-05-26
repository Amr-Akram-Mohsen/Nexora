import re
import hashlib

def validate_email(email: str) -> bool:
    """
    Validates email syntax using a standard RFC 5322 regex.
    """
    if not email:
        return False
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(email_regex, email))

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Enforces strong password guidelines.
    Returns a tuple: (is_strong: bool, error_message: str)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character."
    return True, ""

def hash_token(token: str) -> str:
    """
    Hashes a string token using SHA-256 for secure DB storage.
    """
    if not token:
        return ""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()
