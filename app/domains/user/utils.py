import secrets

def _generate_token():
    return secrets.token_urlsafe(32)