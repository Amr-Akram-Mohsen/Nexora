from flask import current_app, url_for
import smtplib
from email.mime.text import MIMEText

def send_confirmation_email(email, token, unsubscribe_token):
    if not current_app.config.get("MAIL_ENABLED"):
        print("Mail disabled — skipping email")
        return
    
    confirm_url = url_for(
        'main.confirm_subscription',
        token=token,
        _external=True
    )

    unsubscribe_url = url_for(
        'main.unsubscribe_token',
        token=unsubscribe_token,
        _external=True
    )

    # print("CONFIRM LINK:", confirm_url)
    # print("unsubscribe LINK:", unsubscribe_url)

    subject = "Confirm your newsletter subscription"

    body = f"""
Hi,

Please confirm your subscription by clicking the link below:

{confirm_url}

If you didn’t request this, you can ignore this email.

You can unsubscribe anytime:
{unsubscribe_url}

Thanks!
"""

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = current_app.config['MAIL_DEFAULT_SENDER']
    msg['To'] = email

    try:
        with smtplib.SMTP(
            current_app.config['MAIL_SERVER'],
            current_app.config['MAIL_PORT']
        ) as server:
            if current_app.config.get("MAIL_USE_TLS"):
                server.starttls()
            server.login(
                current_app.config['MAIL_USERNAME'],
                current_app.config['MAIL_PASSWORD']
            )
            server.send_message(msg)
    except Exception as e:
        print("Email error:", e)    

