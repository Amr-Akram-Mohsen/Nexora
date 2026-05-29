import logging
from app.domains.user.service import (
    create_user,
    get_user_by_email,
    get_newsletter_subscriber_by_email,
    link_newsletter_subscriber_to_user,
    set_verification_sent,
)
from app.application.user.tokens import generate_verification_token
from app.application.user.email_service import send_verification_email
from app.application.interaction.newsletter import subscribe_workflow

logger = logging.getLogger(__name__)


def register_user_workflow(name: str, email: str, password: str, wants_newsletter: bool = False):
    """
    Full registration workflow:
      1. Guard against duplicate email
      2. Create user (no token stored in DB)
      3. Handle newsletter opt-in
      4. Generate signed verification token & send email
      5. Record verification_sent_at

    Returns (user, newsletter_message | None).
    Returns (None, error_message) on failure.
    """
    if get_user_by_email(email):
        return None, "An account with this email already exists."

    user = create_user(name, email, password)

    # Newsletter opt-in
    newsletter_msg = None
    if wants_newsletter:
        success, msg = subscribe_workflow(email, user.id)
        newsletter_msg = msg if success else f"Account created, but newsletter signup failed: {msg}"
    else:
        # Link pre-existing anonymous subscription
        subscriber = get_newsletter_subscriber_by_email(email)
        if subscriber:
            link_newsletter_subscriber_to_user(subscriber, user.id)

    # Generate stateless signed verification token and send email
    token = generate_verification_token(user.id)
    sent  = send_verification_email(email, token)

    if sent:
        set_verification_sent(user)
        logger.info("[AUTH] Verification email sent to %s (user_id=%s)", email, user.id)
    else:
        logger.warning("[AUTH] Verification email FAILED for %s (user_id=%s)", email, user.id)

    return user, newsletter_msg
