import logging
from flask import Blueprint, request, redirect, flash, render_template, current_app, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from app.core.extensions import limiter, db
from app.shared.utils.logging import log_route_start, log_route_success, log_route_error
from app.application.user.login import (
    authenticate_user,
    check_login_lockout,
    record_failed_login,
    clear_failed_logins,
)
from app.application.user.register import register_user_workflow
from app.application.user.verify import verify_user_email, resend_verification_email_workflow
from app.application.user.password import request_password_reset, reset_user_password
from app.domains.user.service import (
    get_user_by_email,
    get_newsletter_subscriber_by_email,
    get_user_by_id,
)
from app.application.user.profile import (
    update_profile_name_workflow,
    update_profile_password_workflow,
)
from app.application.user.login import handle_successful_login, handle_google_oauth_login

from app.shared.validators import validate_email, validate_password_strength
from app.shared.sanitizer import sanitize_text
import secrets
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)


def is_safe_url(target: str) -> bool:
    ref_url  = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


bp = Blueprint("user", __name__)


# ────────────────────────────────────────────────────────────────────
# LOGIN
# ────────────────────────────────────────────────────────────────────
@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated and not request.args.get('add_account'):
        return redirect(url_for('system.home'))

    try:
        log_route_start(logger, "/login")
        if request.method == 'POST':
            email    = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            remember = request.form.get('remember') == 'on'

            # Lockout guard
            is_locked, _ = check_login_lockout(email)
            if is_locked:
                flash("Too many failed attempts. Please wait 15 minutes before trying again.", "error")
                log_route_success(logger, "/login", template="login.html")
                return render_template('login.html')

            user = authenticate_user(email, password)

            if user:
                if not user.is_verified and user.provider != 'google':
                    flash(
                        "Please verify your email before logging in. "
                        "Check your inbox for the verification link.",
                        "warning",
                    )
                    log_route_success(logger, "/login", template="login.html")
                    return render_template('login.html', show_resend=True, email=email)

                clear_failed_logins(email)

                # Session rotation — prevents session fixation
                existing_accounts = session.get('multi_accounts', [])
                if current_user.is_authenticated and current_user.id not in existing_accounts:
                    existing_accounts.append(current_user.id)
                if user.id not in existing_accounts:
                    existing_accounts.append(user.id)

                session.clear()
                login_user(user, remember=remember)
                if remember:
                    session.permanent = True
                
                session['multi_accounts'] = existing_accounts

                handle_successful_login(user)
                if user.is_admin:
                    log_route_success(logger, "/login", status=302)
                    return redirect(url_for('system.home'))

                next_page = request.args.get('next')
                if not next_page or not is_safe_url(next_page):
                    next_page = url_for('system.home')

                flash(f"Welcome back, {user.name or 'Nexora Member'}! 👋", "success")
                log_route_success(logger, "/login", status=302)
                return redirect(next_page)

            attempts  = record_failed_login(email)
            remaining = max(0, 5 - (attempts or 0))
            if remaining > 0:
                flash(
                    f"Invalid email or password. {remaining} attempt{'s' if remaining != 1 else ''} remaining.",
                    "error",
                )
            else:
                flash("Too many failed attempts. Your account is locked for 15 minutes.", "error")

        log_route_success(logger, "/login", template="login.html")
        return render_template('login.html')
    except Exception as e:
        log_route_error(logger, "/login", e)
        raise


# ────────────────────────────────────────────────────────────────────
# GOOGLE OAUTH
# ────────────────────────────────────────────────────────────────────
@bp.route('/auth/google/login')
def google_login():
    try:
        log_route_start(logger, "/auth/google/login")
        if request.args.get('add_account'):
            session['add_account_flow'] = True
            
        redirect_uri = url_for('user.google_authorize', _external=True)
        log_route_success(logger, "/auth/google/login", status=302)
        return current_app.google.authorize_redirect(redirect_uri, prompt='select_account')
    except Exception as e:
        log_route_error(logger, "/auth/google/login", e)
        raise


@bp.route('/auth/google/authorize')
def google_authorize():
    try:
        log_route_start(logger, "/auth/google/authorize")
        try:
            token     = current_app.google.authorize_access_token()
            user_info = current_app.google.parse_id_token(token, nonce=None)
        except Exception as e:
            logger.error("[AUTH] Google OAuth error: %s", e)
            flash("Google sign-in failed. Please try again.", "error")
            log_route_success(logger, "/auth/google/authorize", status=302)
            return redirect(url_for("user.login"))

        email = user_info.get('email')
        if not email:
            flash("Google did not return an email address.", "error")
            log_route_success(logger, "/auth/google/authorize", status=302)
            return redirect(url_for("user.login"))

        user = handle_google_oauth_login(user_info)


        existing_accounts = session.get('multi_accounts', [])
        is_add_account = session.pop('add_account_flow', False)
        
        if is_add_account and current_user.is_authenticated and current_user.id not in existing_accounts:
            existing_accounts.append(current_user.id)

        session.clear()
        login_user(user)

        if user.id not in existing_accounts:
            existing_accounts.append(user.id)
            
        session['multi_accounts'] = existing_accounts
        flash("Signed in with Google!", "success")
        log_route_success(logger, "/auth/google/authorize", status=302)
        return redirect(url_for('system.home'))
    except Exception as e:
        log_route_error(logger, "/auth/google/authorize", e)
        raise


# ────────────────────────────────────────────────────────────────────
# REGISTER
# ────────────────────────────────────────────────────────────────────
@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for('system.home'))

    try:
        log_route_start(logger, "/register")
        if request.method == 'POST':
            name             = request.form.get('name', '').strip()
            email            = request.form.get('email', '').strip().lower()
            password         = request.form.get('password', '')
            confirm          = request.form.get('confirm_password', '')
            wants_newsletter = request.form.get('newsletter') == 'on'

            sanitized_name = sanitize_text(name)
            if not sanitized_name:
                flash("Please enter your full name.", "error")
                log_route_success(logger, "/register", template="register.html")
                return render_template('register.html')
            if not validate_email(email):
                flash("Please enter a valid email address.", "error")
                log_route_success(logger, "/register", template="register.html")
                return render_template('register.html')
            if password != confirm:
                flash("Passwords do not match.", "error")
                log_route_success(logger, "/register", template="register.html")
                return render_template('register.html')

            is_strong, pwd_err = validate_password_strength(password)
            if not is_strong:
                flash(pwd_err, "error")
                log_route_success(logger, "/register", template="register.html")
                return render_template('register.html')

            user, newsletter_msg, email_sent = register_user_workflow(sanitized_name, email, password, wants_newsletter)

            if not user:
                flash(newsletter_msg or "An account with this email already exists.", "error")
                log_route_success(logger, "/register", template="register.html")
                return render_template('register.html')

            if newsletter_msg:
                flash(newsletter_msg, "info")

            if email_sent:
                flash(
                    "Account created! Please check your email to verify your account before logging in. 📧",
                    "success",
                )
            else:
                flash(
                    "Account created! However, we couldn't send the verification email at this time. Please try resending it later or contact support.",
                    "warning",
                )
            log_route_success(logger, "/register", status=302)
            return redirect(url_for('user.login'))

        log_route_success(logger, "/register", template="register.html")
        return render_template('register.html')
    except Exception as e:
        log_route_error(logger, "/register", e)
        raise


# ────────────────────────────────────────────────────────────────────
# EMAIL VERIFICATION
# ────────────────────────────────────────────────────────────────────
@bp.route('/verify-email/<token>')
def verify_email(token: str):
    try:
        log_route_start(logger, f"/verify-email/{token[:8]}...")
        user, error = verify_user_email(token)

        if error == 'expired':
            flash(
                "This verification link has expired (valid for 24 hours). "
                "Please request a new one below.",
                "warning",
            )
            log_route_success(logger, f"/verify-email/{token[:8]}...", status=302)
            return redirect(url_for('user.login'))

        if error == 'invalid':
            flash("This verification link is invalid or has already been used.", "error")
            log_route_success(logger, f"/verify-email/{token[:8]}...", status=302)
            return redirect(url_for('user.login'))

        session.clear()
        login_user(user)
        handle_successful_login(user)
        flash("Your email has been verified! Welcome to Nexora 🎉", "success")
        log_route_success(logger, f"/verify-email/{token[:8]}...", status=302)
        return redirect(url_for('system.home'))
    except Exception as e:
        log_route_error(logger, f"/verify-email/{token[:8]}...", e)
        raise


@bp.route('/resend-verification', methods=['POST'])
@limiter.limit("3 per minute")
def resend_verification():
    try:
        log_route_start(logger, "/resend-verification")
        email = request.form.get('email', '').strip().lower()
        if email:
            resend_verification_email_workflow(email)
        flash(
            "If that email exists and is unverified, a new link has been sent. "
            "Check your spam folder if you don't see it within a few minutes.",
            "info",
        )
        log_route_success(logger, "/resend-verification", status=302)
        return redirect(url_for('user.login'))
    except Exception as e:
        log_route_error(logger, "/resend-verification", e)
        raise


# ────────────────────────────────────────────────────────────────────
# FORGOT / RESET PASSWORD
# ────────────────────────────────────────────────────────────────────
@bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def forgot_password():
    try:
        log_route_start(logger, "/forgot-password")
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            request_password_reset(email)
            flash(
                "If an account with that email exists, a password reset link has been sent. "
                "The link expires in 1 hour.",
                "info",
            )
            log_route_success(logger, "/forgot-password", status=302)
            return redirect(url_for('user.login'))
        
        log_route_success(logger, "/forgot-password", template="forgot-password.html")
        return render_template('forgot-password.html')
    except Exception as e:
        log_route_error(logger, "/forgot-password", e)
        raise


@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token: str):
    try:
        log_route_start(logger, f"/reset-password/{token[:8]}...")
        if request.method == 'POST':
            password = request.form.get('password', '')
            confirm  = request.form.get('confirm_password', '')

            if password != confirm:
                flash("Passwords do not match.", "error")
                log_route_success(logger, f"/reset-password/{token[:8]}...", template="reset-password.html")
                return render_template('reset-password.html', token=token)

            is_strong, pwd_err = validate_password_strength(password)
            if not is_strong:
                flash(pwd_err, "error")
                log_route_success(logger, f"/reset-password/{token[:8]}...", template="reset-password.html")
                return render_template('reset-password.html', token=token)

            success, msg = reset_user_password(token, password)
            if success:
                flash(msg, "success")
                log_route_success(logger, f"/reset-password/{token[:8]}...", status=302)
                return redirect(url_for('user.login'))
            else:
                flash(msg, "error")
                log_route_success(logger, f"/reset-password/{token[:8]}...", status=302)
                # Redirect expired/used tokens to forgot-password; invalid tokens back to login
                if "expired" in msg.lower() or "already been used" in msg.lower():
                    return redirect(url_for('user.forgot_password'))
                return redirect(url_for('user.login'))

        log_route_success(logger, f"/reset-password/{token[:8]}...", template="reset-password.html")
        return render_template('reset-password.html', token=token)
    except Exception as e:
        log_route_error(logger, f"/reset-password/{token[:8]}...", e)
        raise


# ────────────────────────────────────────────────────────────────────
# LOGOUT
# ────────────────────────────────────────────────────────────────────
@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    try:
        log_route_start(logger, "/logout")
        
        existing_accounts = session.get('multi_accounts', [])
        if current_user.id in existing_accounts:
            existing_accounts.remove(current_user.id)
            
        logout_user()
        
        if existing_accounts:
            next_user_id = existing_accounts[0]
            next_user = get_user_by_id(next_user_id)
            if next_user:
                login_user(next_user)
                session['multi_accounts'] = existing_accounts
                flash(f"Logged out. Switched to {next_user.name or next_user.email}.", "info")
                log_route_success(logger, "/logout", status=302)
                return redirect(url_for('system.home'))

        session.pop('multi_accounts', None)
        flash("You have been logged out.", "info")
        log_route_success(logger, "/logout", status=302)
        return redirect(url_for('system.home'))
    except Exception as e:
        log_route_error(logger, "/logout", e)
        raise

@bp.route('/logout-all', methods=['POST'])
@login_required
def logout_all():
    try:
        log_route_start(logger, "/logout-all")
        logout_user()
        session.pop('multi_accounts', None)
        flash("You have been logged out of all accounts.", "info")
        log_route_success(logger, "/logout-all", status=302)
        return redirect(url_for('system.home'))
    except Exception as e:
        log_route_error(logger, "/logout-all", e)
        raise

@bp.route('/switch-account/<int:user_id>', methods=['POST'])
@login_required
def switch_account(user_id):
    try:
        log_route_start(logger, f"/switch-account/{user_id}")
        existing_accounts = session.get('multi_accounts', [])
        
        if user_id in existing_accounts:
            target_user = get_user_by_id(user_id)
            if target_user:
                logout_user()
                login_user(target_user)
                flash(f"Switched to {target_user.name or target_user.email}", "success")
            else:
                existing_accounts.remove(user_id)
                session['multi_accounts'] = existing_accounts
                flash("Account not found. It may have been deleted.", "error")
        else:
            flash("Unauthorized account switch.", "error")
            
        log_route_success(logger, f"/switch-account/{user_id}", status=302)
        return redirect(request.referrer or url_for('system.home'))
    except Exception as e:
        log_route_error(logger, f"/switch-account/{user_id}", e)
        raise


# ────────────────────────────────────────────────────────────────────
# PROFILE
# ────────────────────────────────────────────────────────────────────
@bp.route('/profile')
@login_required
def profile():
    try:
        log_route_start(logger, "/profile")
        subscriber = get_newsletter_subscriber_by_email(current_user.email)
        
        # Load collections
        from app.application.interaction.get_saved import get_saved_articles_workflow, get_saved_products_workflow
        saved_articles = get_saved_articles_workflow(current_user.id)
        saved_items = get_saved_products_workflow(current_user.id)
        
        collections_map = {}
        for item in saved_articles + saved_items:
            c_name = item.get("collection_name", "General")
            collections_map[c_name] = collections_map.get(c_name, 0) + 1
            
        collections = [{"name": k, "count": v} for k, v in collections_map.items()]
        collections.sort(key=lambda x: x["name"])
        
        log_route_success(logger, "/profile", template="profile.html")
        return render_template('profile.html', subscriber=subscriber, collections=collections)
    except Exception as e:
        log_route_error(logger, "/profile", e)
        raise

@bp.route('/history')
@login_required
def history():
    try:
        log_route_start(logger, "/history")
        from app.application.interaction.get_history import get_reading_history_workflow
        history_items = get_reading_history_workflow(current_user.id, limit=50)
        log_route_success(logger, "/history", template="history.html")
        return render_template('history.html', history_items=history_items)
    except Exception as e:
        log_route_error(logger, "/history", e)
        raise


@bp.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    try:
        log_route_start(logger, "/update-profile")
        action = request.form.get('action')

        if action == 'name':
            name = request.form.get('name', '').strip()
            sanitized_name = sanitize_text(name)
            if not sanitized_name:
                flash("Display name cannot be empty.", "error")
            else:
                update_profile_name_workflow(current_user, sanitized_name)
                flash("Display name updated.", "success")

        elif action == 'password':
            if current_user.provider == 'google':
                flash("Google accounts cannot change password here.", "error")
                log_route_success(logger, "/update-profile", status=302)
                return redirect(url_for('user.profile'))

            current_pwd = request.form.get('current_password', '')
            new_pwd     = request.form.get('new_password', '')
            confirm_pwd = request.form.get('confirm_new_password', '')

            if not current_user.check_password(current_pwd):
                flash("Incorrect current password.", "error")
            elif new_pwd != confirm_pwd:
                flash("New passwords do not match.", "error")
            else:
                is_strong, pwd_err = validate_password_strength(new_pwd)
                if not is_strong:
                    flash(pwd_err, "error")
                else:
                    update_profile_password_workflow(current_user, new_pwd)
                    flash("Password changed successfully!", "success")

        log_route_success(logger, "/update-profile", status=302)
        return redirect(url_for('user.profile'))
    except Exception as e:
        log_route_error(logger, "/update-profile", e)
        raise
@bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    try:
        log_route_start(logger, "/delete-account")
        password = request.form.get('password')
        
        if current_user.provider != 'google':
            if not password or not current_user.check_password(password):
                flash("Incorrect password. Account deletion failed.", "error")
                return redirect(url_for('user.profile'))
                
        # Delete user
        from app.core.extensions import db
        db.session.delete(current_user)
        db.session.commit()
        
        logout_user()
        flash("Your account has been permanently deleted.", "success")
        log_route_success(logger, "/delete-account", status=302)
        return redirect(url_for('system.home'))
    except Exception as e:
        log_route_error(logger, "/delete-account", e)
        flash("An error occurred during account deletion.", "error")
        return redirect(url_for('user.profile'))
