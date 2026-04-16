import secrets
from datetime import datetime, timezone, timedelta
from flask import request, redirect, flash, render_template, current_app, url_for
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import limiter
from app.models import db, User, NewsletterSubscriber
from app.utils.email import (
    send_confirmation_email,
    send_verification_email,
    send_password_reset_email,
)
from . import bp


# ── Helpers ──────────────────────────────────────────────────────────
def _generate_token():
    return secrets.token_urlsafe(32)


# ────────────────────────────────────────────────────────────────────
# LOGIN
# ────────────────────────────────────────────────────────────────────
@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.is_verified and user.provider != 'google':
                flash('Your account is not verified yet. 📧 Check your inbox for a verification link.', 'warning')
                return render_template('login.html', show_resend=True, email=email)
            
            # 🔐 Safe login
            login_user(user, remember=remember)
            if remember:
                from flask import session
                session.permanent = True
            
            next_page = request.args.get('next')
            # 🛡️ Prevent Open Redirect vulnerability
            if not next_page or not next_page.startswith('/') or next_page.startswith('//'):
                next_page = url_for('main.home')
                
            flash(f'Welcome back, {user.name or "Nexora Member"}! 👋', 'success')
            return redirect(next_page)
            
        flash('Invalid email or password. Please try again.', 'error')
    
    return render_template('login.html')



# ────────────────────────────────────────────────────────────────────
# GOOGLE OAUTH
# ────────────────────────────────────────────────────────────────────
@bp.route('/auth/google/login')
def google_login():
    redirect_uri = url_for('main.google_authorize', _external=True)
    return current_app.google.authorize_redirect(redirect_uri, prompt='select_account')


@bp.route('/auth/google/authorize')
def google_authorize():
    try:
        token = current_app.google.authorize_access_token()
        user_info = current_app.google.parse_id_token(token, nonce=None)
    except Exception as e:
        current_app.logger.error("GOOGLE OAUTH ERROR: %s", e)
        flash(f"Google login failed: {str(e)}", "error")
        return redirect(url_for("main.login"))

    email = user_info.get('email')
    if not email:
        flash("Google did not return an email address.", "error")
        return redirect(url_for("main.login"))

    user = User.query.filter_by(email=email).first()
    if user:
        if not user.google_id:
            user.google_id = user_info.get('sub')
            user.provider = 'google'
            user.is_verified = True  # Google accounts are pre-verified
            db.session.commit()
    else:
        user = User(
            email=email,
            name=user_info.get('name'),
            provider='google',
            google_id=user_info.get('sub'),
            is_verified=True,  # Google accounts are pre-verified
        )
        user.set_password(secrets.token_urlsafe(24))
        db.session.add(user)
        db.session.commit()

    login_user(user)
    flash("Successfully signed in with Google!", "success")
    return redirect(url_for('main.home'))


# ────────────────────────────────────────────────────────────────────
# REGISTER
# ────────────────────────────────────────────────────────────────────
@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        name    = request.form.get('name', '').strip()
        email   = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')

        # ── Validation ──────────────────────────────────────────────
        if not name:
            flash('Please enter your full name.', 'error')
            return render_template('register.html')
        if not email or '@' not in email:
            flash('Please enter a valid email address.', 'error')
            return render_template('register.html')
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return render_template('register.html')
        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'error')
            return render_template('register.html')

        # ── Create user (unverified) ─────────────────────────────────
        verification_token = _generate_token()
        user = User(
            email=email,
            name=name,
            is_verified=False,
            verification_token=verification_token,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()   # get user.id

        # ── Newsletter opt-in ────────────────────────────────────────
        # Match 'newsletter' from base-auth.html
        wants_newsletter = request.form.get('newsletter') == 'on'
        newsletter_msg = None
        subscriber = NewsletterSubscriber.query.filter_by(email=email).first()
        
        if subscriber:
            subscriber.user_id = user.id
            if wants_newsletter and not subscriber.is_confirmed:
                newsletter_msg = 'Your existing newsletter subscription was linked 🎯'
        elif wants_newsletter:
            subscriber = NewsletterSubscriber(email=email, user_id=user.id)
            subscriber.generate_tokens()
            db.session.add(subscriber)
            send_confirmation_email(subscriber.email, subscriber.confirmation_token, subscriber.unsubscribe_token)
            newsletter_msg = 'Newsletter confirmation sent to your email 📬'

        db.session.commit()

        # ── Send verification email ──────────────────────────────────
        send_verification_email(email, verification_token)

        if newsletter_msg:
            flash(newsletter_msg, 'info')
        flash('Account created! Please check your email to verify your account before logging in. 📧', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html')



# ────────────────────────────────────────────────────────────────────
# EMAIL VERIFICATION
# ────────────────────────────────────────────────────────────────────
@bp.route('/verify-email/<token>')
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    if not user:
        flash('Invalid or expired verification link.', 'error')
        return redirect(url_for('main.login'))
    user.is_verified = True
    user.verification_token = None
    db.session.commit()
    login_user(user)
    flash('Your email has been verified! Welcome to Nexora 🎉', 'success')
    return redirect(url_for('main.home'))


@bp.route('/resend-verification', methods=['POST'])
@limiter.limit("3 per minute")
def resend_verification():
    email = request.form.get('email', '').strip().lower()
    user = User.query.filter_by(email=email, is_verified=False).first()
    if user:
        token = _generate_token()
        user.verification_token = token
        db.session.commit()
        send_verification_email(email, token)
    flash('If that email exists and is unverified, a new link has been sent.', 'info')
    return redirect(url_for('main.login'))


# ────────────────────────────────────────────────────────────────────
# FORGOT / RESET PASSWORD
# ────────────────────────────────────────────────────────────────────
@bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and user.provider != 'google':  # Google users use Google's reset
            token = _generate_token()
            user.reset_token = token
            user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            db.session.commit()
            send_password_reset_email(email, token)
        # Always show the same message to prevent email enumeration
        flash('If an account with that email exists, a password reset link has been sent.', 'info')
        return redirect(url_for('main.login'))
    return render_template('forgot-password.html')


@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    now = datetime.now(timezone.utc)

    if not user or not user.reset_token_expires_at:
        flash('Invalid or expired password reset link.', 'error')
        return redirect(url_for('main.forgot_password'))

    expires = user.reset_token_expires_at
    if expires.tzinfo is None:
        from datetime import timezone as _tz
        expires = expires.replace(tzinfo=_tz.utc)
    if now > expires:
        flash('This password reset link has expired. Please request a new one.', 'error')
        return redirect(url_for('main.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return render_template('reset-password.html', token=token)
        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('reset-password.html', token=token)
        user.set_password(password)
        user.reset_token = None
        user.reset_token_expires_at = None
        db.session.commit()
        flash('Password updated successfully! You can now log in. 🔐', 'success')
        return redirect(url_for('main.login'))

    return render_template('reset-password.html', token=token)


# ────────────────────────────────────────────────────────────────────
# LOGOUT
# ────────────────────────────────────────────────────────────────────
@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.home'))



