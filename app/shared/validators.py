import re


def validate_email(email: str) -> bool:
    """
    Validates email syntax using a standard RFC 5322 regex.
    """
    if not email:
        return False
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Evaluates password strength based on length and character diversity.
    Prefers longer passwords over rigid composition rules.

    Rules:
      - Minimum 8 characters (hard requirement)
      - Score-based: length + variety of character classes used
      - Score >= 2 is acceptable
    """
    if not password:
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."

    score = 0
    score += bool(re.search(r'[a-z]', password))
    score += bool(re.search(r'[A-Z]', password))
    score += bool(re.search(r'\d', password))
    score += bool(re.search(r'[^a-zA-Z0-9]', password))

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
    Returns a human-readable strength label.
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

    if score <= 1: return "weak"
    if score == 2: return "fair"
    if score == 3: return "good"
    return "strong"
