from flask import Blueprint, request, redirect, flash, render_template, current_app, url_for, abort, session
from flask_login import login_user, logout_user, login_required, current_user
from app.core.extensions import limiter
from app.application.user.login import authenticate_user
from app.application.user.register import register_user_workflow
from app.application.user.verify import verify_user_email, resend_verification_email_workflow
from app.application.user.password import request_password_reset, reset_user_password
from app.domains.user.service import (
    get_user_by_email,
    get_newsletter_subscriber_by_email,
    update_user_name,
    update_user_password
)
import secrets
from urllib.parse import urlparse, urljoin

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

bp = Blueprint("user", __name__)

# ────────────────────────────────────────────────────────────────────
# LOGIN
# ────────────────────────────────────────────────────────────────────
@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.home'))
        return redirect(url_for('system.home'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'
        
        # 🛡️ Lockout Check
        from app.application.user.login import check_login_lockout, record_failed_login, clear_failed_logins
        is_locked, mins = check_login_lockout(email)
        if is_locked:
            flash(f"Too many failed attempts. This account is locked for 15 minutes.", "error")
            return render_template('login.html')
            
        user = authenticate_user(email, password)
        
        if user:
            if not user.is_verified and user.provider != 'google':
                flash('Your account is not verified yet. 📧 Check your inbox for a verification link.', 'warning')
                return render_template('login.html', show_resend=True, email=email)
            
            # Clear lockout attempts on success
            clear_failed_logins(email)
            
            # 🔐 Safe login & Session rotation to prevent session fixation
            session.clear()
            login_user(user, remember=remember)
            if remember:
                session.permanent = True
            
            if user.is_admin:
                return redirect(url_for('admin.home'))
            
            next_page = request.args.get('next')
            if not next_page or not is_safe_url(next_page):
                next_page = url_for('system.home')
                
            flash(f'Welcome back, {user.name or "Nexora Member"}! 👋', 'success')
            return redirect(next_page)
            
        # Record failed attempt
        record_failed_login(email)
        flash('Invalid email or password. Please try again.', 'error')
    
    return render_template('login.html')

# ────────────────────────────────────────────────────────────────────
# GOOGLE OAUTH
# ────────────────────────────────────────────────────────────────────
@bp.route('/auth/google/login')
def google_login():
    redirect_uri = url_for('user.google_authorize', _external=True)
    return current_app.google.authorize_redirect(redirect_uri, prompt='select_account')


@bp.route('/auth/google/authorize')
def google_authorize():
    try:
        token = current_app.google.authorize_access_token()
        user_info = current_app.google.parse_id_token(token, nonce=None)
    except Exception as e:
        current_app.logger.error("GOOGLE OAUTH ERROR: %s", e)
        flash(f"Google login failed: {str(e)}", "error")
        return redirect(url_for("user.login"))

    email = user_info.get('email')
    if not email:
        flash("Google did not return an email address.", "error")
        return redirect(url_for("user.login"))

    # TODO: Move to Application Layer
    from app.core.extensions import db
    from app.domains.user.models import User
    user = get_user_by_email(email)
    if user:
        if not user.google_id:
            user.google_id = user_info.get('sub')
            user.provider = 'google'
            user.is_verified = True
            db.session.commit()
    else:
        user = User(
            email=email,
            name=user_info.get('name'),
            provider='google',
            google_id=user_info.get('sub'),
            is_verified=True,
        )
        user.set_password(secrets.token_urlsafe(24))
        db.session.add(user)
        db.session.commit()

    login_user(user)
    flash("Successfully signed in with Google!", "success")
    return redirect(url_for('system.home'))

# ────────────────────────────────────────────────────────────────────
# REGISTER
# ────────────────────────────────────────────────────────────────────
@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for('system.home'))
    if request.method == 'POST':
        name    = request.form.get('name', '').strip()
        email   = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')

        from app.shared.validators import validate_email, validate_password_strength
        from app.shared.sanitizer import sanitize_text

        sanitized_name = sanitize_text(name)

        if not sanitized_name:
            flash('Please enter your full name.', 'error')
            return render_template('register.html')
        if not validate_email(email):
            flash('Please enter a valid email address.', 'error')
            return render_template('register.html')
        
        is_strong, pwd_err = validate_password_strength(password)
        if not is_strong:
            flash(pwd_err, 'error')
            return render_template('register.html')
        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        wants_newsletter = request.form.get('newsletter') == 'on'
        user, newsletter_msg = register_user_workflow(sanitized_name, email, password, wants_newsletter)

        if not user:
            flash(newsletter_msg or 'An account with this email already exists.', 'error')
            return render_template('register.html')

        if newsletter_msg:
            flash(newsletter_msg, 'info')
        flash('Account created! Please check your email to verify your account before logging in. 📧', 'success')
        return redirect(url_for('user.login'))
    return render_template('register.html')

# ────────────────────────────────────────────────────────────────────
# EMAIL VERIFICATION
# ────────────────────────────────────────────────────────────────────
@bp.route('/verify-email/<token>')
def verify_email(token):
    user = verify_user_email(token)
    if not user:
        flash('Invalid or expired verification link.', 'error')
        return redirect(url_for('user.login'))
    
    login_user(user)
    flash('Your email has been verified! Welcome to Nexora 🎉', 'success')
    return redirect(url_for('system.home'))


@bp.route('/resend-verification', methods=['POST'])
@limiter.limit("3 per minute")
def resend_verification():
    email = request.form.get('email', '').strip().lower()
    resend_verification_email_workflow(email)
    flash('If that email exists and is unverified, a new link has been sent.', 'info')
    return redirect(url_for('user.login'))

# ────────────────────────────────────────────────────────────────────
# FORGOT / RESET PASSWORD
# ────────────────────────────────────────────────────────────────────
@bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        request_password_reset(email)
        flash('If an account with that email exists, a password reset link has been sent.', 'info')
        return redirect(url_for('user.login'))
    return render_template('forgot-password.html')


@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')
        
        from app.shared.validators import validate_password_strength
        is_strong, pwd_err = validate_password_strength(password)
        if not is_strong:
            flash(pwd_err, 'error')
            return render_template('reset-password.html', token=token)
        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('reset-password.html', token=token)
        
        success, msg = reset_user_password(token, password)
        if success:
            flash(msg, 'success')
            return redirect(url_for('user.login'))
        else:
            flash(msg, 'error')
            return redirect(url_for('user.forgot_password'))

    return render_template('reset-password.html', token=token)

# ────────────────────────────────────────────────────────────────────
# LOGOUT
# ────────────────────────────────────────────────────────────────────
@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('system.home'))

@bp.route('/profile')
@login_required
def profile():
    subscriber = get_newsletter_subscriber_by_email(current_user.email)
    return render_template('profile.html', subscriber=subscriber)

@bp.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    action = request.form.get('action')
    if action == 'name':
        name = request.form.get('name', '').strip()
        from app.shared.sanitizer import sanitize_text
        sanitized_name = sanitize_text(name)
        if not sanitized_name:
            flash('Display name cannot be empty.', 'error')
        else:
            update_user_name(current_user, sanitized_name)
            flash('Display name updated successfully.', 'success')
    elif action == 'password':
        if current_user.provider == 'google':
            flash('Google accounts cannot change password here.', 'error')
            return redirect(url_for('user.profile'))
        
        current_pwd_input = request.form.get('current_password', '')
        new_pwd = request.form.get('new_password', '')
        confirm_pwd = request.form.get('confirm_new_password', '')
        
        if not current_user.check_password(current_pwd_input):
            flash('Incorrect current password.', 'error')
        else:
            from app.shared.validators import validate_password_strength
            is_strong, pwd_err = validate_password_strength(new_pwd)
            if not is_strong:
                flash(pwd_err, 'error')
            elif new_pwd != confirm_pwd:
                flash('New passwords do not match.', 'error')
            else:
                update_user_password(current_user, new_pwd)
                flash('Password changed successfully!', 'success')
    return redirect(url_for('user.profile'))
