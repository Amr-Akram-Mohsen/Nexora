from app.domains.user.service import get_active_user_by_email

def authenticate_user(email, password):
    """
    Authenticates a user and returns the user object if successful.
    """
    user = get_active_user_by_email(email)
    if user and user.check_password(password):
        return user
    return None
