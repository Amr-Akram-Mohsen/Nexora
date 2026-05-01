from app.domains.user.service import get_user_by_verification_token, verify_user

def verify_user_email(token):
    """
    Verifies a user's email using a token.
    """
    user = get_user_by_verification_token(token)
    if not user:
        return None
    
    return verify_user(user)
