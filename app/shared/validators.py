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
    Evaluates password strength based on length and character diversity.
    Prefers longer passwords over rigid composition rules.

    Rules:
      - Minimum 8 characters (hard requirement)
      - Score-based: length + variety of character classes used
      - Score >= 2 is acceptable; gives a helpful, specific message if not
    """
    if not password:
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."

    # Award points for character class diversity
    score = 0
    has_lower   = bool(re.search(r'[a-z]', password))
    has_upper   = bool(re.search(r'[A-Z]', password))
    has_digit   = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[^a-zA-Z0-9]', password))

    score += has_lower
    score += has_upper
    score += has_digit
    score += has_special

    # Bonus for length beyond minimum
    if len(password) >= 12:
        score += 1
    if len(password) >= 16:
        score += 1

    if score < 2:
        return (
            False,
            "Password is too weak. Mix letters, numbers, or symbols to make it stronger.",
        )

    return True, ""


def password_strength_label(password: str) -> str:
    """
    Returns a human-readable strength label for client-side display.
    Values: 'weak' | 'fair' | 'good' | 'strong'
    """
    if not password or len(password) < 8:
        return "weak"

    score = 0
    score += bool(re.search(r'[a-z]', password))
    score += bool(re.search(r'[A-Z]', password))
    score += bool(re.search(r'\d', password))
    score += bool(re.search(r'[^a-zA-Z0-9]', password))
    if len(password) >= 12:
        score += 1
    if len(password) >= 16:
        score += 1

    if score <= 1:
        return "weak"
    if score == 2:
        return "fair"
    if score == 3:
        return "good"
    return "strong"


def hash_token(token: str) -> str:
    """
    Hashes a string token using SHA-256 for secure DB storage.
    """
    if not token:
        return ""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()
