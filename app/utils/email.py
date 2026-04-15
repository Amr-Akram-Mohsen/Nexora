# app/utils/email.py
"""
Centralised email sending using Flask-Mail.
All mail goes through the mail extension from app.extensions.
Falls back gracefully when MAIL_ENABLED=False.
"""
import logging
from flask import current_app, url_for, render_template_string
from flask_mail import Message
from app.extensions import mail

logger = logging.getLogger(__name__)


def _enabled():
    return current_app.config.get("MAIL_ENABLED", False)


def _send(msg: Message):
    if not _enabled():
        logger.info("MAIL_ENABLED=False — skipping email to %s", msg.recipients)
        return
    try:
        mail.send(msg)
        logger.info("Email sent to %s: %s", msg.recipients, msg.subject)
    except Exception as e:
        logger.error("Failed to send email to %s: %s", msg.recipients, e)


# ── Newsletter confirmation ───────────────────────────────────────────────────
def send_confirmation_email(email: str, token: str, unsubscribe_token: str):
    confirm_url = url_for(
        'main.confirm_subscription', token=token, _external=True
    )
    unsubscribe_url = url_for(
        'main.unsubscribe_token', token=unsubscribe_token, _external=True
    )

    body = _newsletter_html(confirm_url, unsubscribe_url)
    msg = Message(
        subject="Confirm your Nexora newsletter subscription",
        sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
        recipients=[email],
        html=body,
        body=(
            f"Please confirm your subscription:\n{confirm_url}\n\n"
            f"Unsubscribe anytime:\n{unsubscribe_url}"
        ),
    )
    _send(msg)


# ── Email verification (account) ─────────────────────────────────────────────
def send_verification_email(email: str, token: str):
    verify_url = url_for('main.verify_email', token=token, _external=True)

    body = _verification_html(verify_url, email)
    msg = Message(
        subject="Verify your Nexora account",
        sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
        recipients=[email],
        html=body,
        body=f"Verify your email:\n{verify_url}\n\nThis link expires in 24 hours.",
    )
    _send(msg)


# ── Password reset ────────────────────────────────────────────────────────────
def send_password_reset_email(email: str, token: str):
    reset_url = url_for('main.reset_password', token=token, _external=True)

    body = _reset_html(reset_url)
    msg = Message(
        subject="Reset your Nexora password",
        sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
        recipients=[email],
        html=body,
        body=(
            f"Reset your password here:\n{reset_url}\n\n"
            "This link expires in 1 hour. If you did not request this, ignore this email."
        ),
    )
    _send(msg)


# ── HTML Templates ────────────────────────────────────────────────────────────
def _base_email(title: str, preheader: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#f4f4f8;font-family:'Inter',Arial,sans-serif;">
  <div style="max-width:600px;margin:40px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08);">
    <!-- Header -->
    <div style="background:linear-gradient(135deg,#3b82f6 0%,#8b5cf6 100%);padding:32px 40px;">
      <h1 style="margin:0;color:#fff;font-size:26px;font-weight:800;letter-spacing:-0.5px;">⚡ Nexora</h1>
      <p style="margin:8px 0 0;color:rgba(255,255,255,.8);font-size:14px;">{preheader}</p>
    </div>
    <!-- Body -->
    <div style="padding:40px;">
      {body_html}
    </div>
    <!-- Footer -->
    <div style="padding:24px 40px;background:#f9f9fc;border-top:1px solid #e5e7eb;text-align:center;">
      <p style="margin:0;font-size:12px;color:#9ca3af;">
        © 2025 Nexora. Your trusted source for tech &amp; lifestyle in KSA &amp; UAE.
      </p>
    </div>
  </div>
</body>
</html>"""


def _btn(url: str, label: str, color: str = "#3b82f6") -> str:
    return (
        f'<a href="{url}" style="display:inline-block;background:{color};'
        f'color:#fff;padding:14px 32px;border-radius:8px;text-decoration:none;'
        f'font-weight:700;font-size:16px;margin-top:24px;">{label}</a>'
    )


def _newsletter_html(confirm_url: str, unsub_url: str) -> str:
    body = f"""
      <h2 style="margin:0 0 12px;color:#111;font-size:22px;font-weight:700;">Confirm your subscription 📬</h2>
      <p style="color:#555;line-height:1.7;">Thanks for signing up for the <strong>Nexora Newsletter</strong>!
      Click the button below to confirm your email address and start receiving the latest tech news, reviews, and exclusive deals.</p>
      {_btn(confirm_url, "✅ Confirm Subscription")}
      <p style="margin-top:32px;font-size:13px;color:#9ca3af;">
        Didn't sign up? You can safely ignore this email.<br>
        <a href="{unsub_url}" style="color:#9ca3af;">Unsubscribe</a>
      </p>"""
    return _base_email("Confirm your subscription", "One click to confirm", body)


def _verification_html(verify_url: str, email: str) -> str:
    body = f"""
      <h2 style="margin:0 0 12px;color:#111;font-size:22px;font-weight:700;">Verify your email 🔐</h2>
      <p style="color:#555;line-height:1.7;">Welcome to <strong>Nexora</strong>! Your account was created for
      <strong>{email}</strong>. Click the button below to verify your email and activate your account.</p>
      {_btn(verify_url, "✅ Verify My Email")}
      <p style="margin-top:32px;font-size:13px;color:#9ca3af;">This link expires in 24 hours. If you did not create an account, ignore this email.</p>"""
    return _base_email("Verify your Nexora account", "Activate your account", body)


def _reset_html(reset_url: str) -> str:
    body = f"""
      <h2 style="margin:0 0 12px;color:#111;font-size:22px;font-weight:700;">Reset your password 🔑</h2>
      <p style="color:#555;line-height:1.7;">We received a request to reset your <strong>Nexora</strong> password.
      Click the button below to choose a new password. This link expires in <strong>1 hour</strong>.</p>
      {_btn(reset_url, "🔑 Reset Password", "#8b5cf6")}
      <p style="margin-top:32px;font-size:13px;color:#9ca3af;">If you did not request a password reset, you can safely ignore this email — your password will not change.</p>"""
    return _base_email("Reset your Nexora password", "Secure password reset", body)
