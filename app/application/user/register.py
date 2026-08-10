import logging
from app.domains.user.service import (
    create_user,
    get_user_by_email,
    get_newsletter_subscriber_by_email,
    link_newsletter_subscriber_to_user,
    set_verification_sent,
)
from app.application.user.otp import generate_otp
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
    logger.info("[AUTH] Registration workflow start for email: %s", email)
    if get_user_by_email(email):
        logger.info("[AUTH] Registration aborted: account with email %s already exists.", email)
        return None, "An account with this email already exists.", False

    user = create_user(name, email, password)
    logger.info("[AUTH] User created in DB with user_id=%s for email: %s", user.id, email)

    # Newsletter opt-in
    newsletter_msg = None
    if wants_newsletter:
        logger.info("[AUTH] User opted into newsletter for user_id=%s", user.id)
        success, msg = subscribe_workflow(email, user.id)
        newsletter_msg = msg if success else f"Account created, but newsletter signup failed: {msg}"
    else:
        # Link pre-existing anonymous subscription
        subscriber = get_newsletter_subscriber_by_email(email)
        if subscriber:
            logger.info("[AUTH] Linking existing newsletter subscription to user_id=%s", user.id)
            link_newsletter_subscriber_to_user(subscriber, user.id)

    # Generate OTP code and send email
    code = generate_otp(email, "register")
    sent  = send_verification_email(email, code)

    if sent:
        set_verification_sent(user)
        logger.info("[AUTH] Verification email sent to %s (user_id=%s)", email, user.id)
    else:
        logger.warning("[AUTH] Verification email FAILED to send to %s (user_id=%s)", email, user.id)

    from app.core.extensions import db
    db.session.commit()

    return user, newsletter_msg, sent
