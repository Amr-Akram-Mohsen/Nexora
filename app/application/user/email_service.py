"""
app/application/user/email_service.py
Centralised email templates and dispatch orchestration.
Delegates transport to app/integrations/email/client.py.
"""
import logging
from flask import url_for
from app.integrations.email.client import send_email

logger = logging.getLogger(__name__)


# ── Newsletter confirmation ────────────────────────────────────────────────────
def send_confirmation_email(email: str, token: str, unsubscribe_token: str) -> bool:
    confirm_url = url_for(
        'interaction.confirm_subscription', token=token, _external=True
    )
    unsubscribe_url = url_for(
        'interaction.unsubscribe_token', token=unsubscribe_token, _external=True
    )
    logger.info("[AUTH] Generating newsletter confirmation email for %s | url: %s", email, confirm_url)
    
    html = _newsletter_html(confirm_url, unsubscribe_url)
    text = (
        f"Please confirm your subscription:\n{confirm_url}\n\n"
        f"Unsubscribe anytime:\n{unsubscribe_url}"
    )
    
    return send_email(
        subject="Confirm your Nexora newsletter subscription",
        recipients=[email],
        body=text,
        html=html
    )


# ── Email verification (account) ──────────────────────────────────────────────
def send_verification_email(email: str, code: str) -> bool:
    logger.info("[AUTH] Generating email verification code for %s | code: %s", email, code)
    
    html = _verification_html(code, email)
    text = f"Verify your email. Your code is: {code}\n\nThis code expires in 15 minutes."
    
    return send_email(
        subject="Verify your Nexora account",
        recipients=[email],
        body=text,
        html=html
    )


# ── Password reset ─────────────────────────────────────────────────────────────
def send_password_reset_email(email: str, code: str) -> bool:
    logger.info("[AUTH] Generating password reset code for %s | code: %s", email, code)
    
    html = _reset_html(code)
    text = (
        f"Reset your password. Your code is: {code}\n\n"
        "This code expires in 15 minutes. If you did not request this, ignore this email."
    )
    
    return send_email(
        subject="Reset your Nexora password",
        recipients=[email],
        body=text,
        html=html
    )


# ── HTML Templates ─────────────────────────────────────────────────────────────
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


def _verification_html(code: str, email: str) -> str:
    body = f"""
      <h2 style="margin:0 0 12px;color:#111;font-size:22px;font-weight:700;">Verify your email 🔐</h2>
      <p style="color:#555;line-height:1.7;">Welcome to <strong>Nexora</strong>! Your account was created for
      <strong>{email}</strong>. Please enter the following 6-digit code to verify your email and activate your account.</p>
      <div style="background:#f4f4f8;padding:20px;border-radius:8px;text-align:center;font-size:32px;font-weight:800;letter-spacing:4px;color:#3b82f6;margin:24px 0;">
        {code}
      </div>
      <p style="margin-top:32px;font-size:13px;color:#9ca3af;">This code expires in 15 minutes. If you did not create an account, ignore this email.</p>"""
    return _base_email("Verify your Nexora account", "Activate your account", body)


def _reset_html(code: str) -> str:
    body = f"""
      <h2 style="margin:0 0 12px;color:#111;font-size:22px;font-weight:700;">Reset your password 🔑</h2>
      <p style="color:#555;line-height:1.7;">We received a request to reset your <strong>Nexora</strong> password.
      Please enter the following 6-digit code to choose a new password.</p>
      <div style="background:#f4f4f8;padding:20px;border-radius:8px;text-align:center;font-size:32px;font-weight:800;letter-spacing:4px;color:#8b5cf6;margin:24px 0;">
        {code}
      </div>
      <p style="margin-top:32px;font-size:13px;color:#9ca3af;">This code expires in <strong>15 minutes</strong>. If you did not request a password reset, you can safely ignore this email — your password will not change.</p>"""
    return _base_email("Reset your Nexora password", "Secure password reset", body)
