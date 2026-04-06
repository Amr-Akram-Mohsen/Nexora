import secrets
from flask import request, redirect, flash, render_template, current_app, url_for
from flask_login import login_user, logout_user, login_required

from app.extensions import limiter
from app.models import db, User, NewsletterSubscriber
from app.utils.email import send_confirmation_email
from . import bp

# ------------------------
# Login route
# ------------------------

@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.home'))
        flash('Invalid email or password', 'error')
    return render_template('login.html')

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
        print("GOOGLE OAUTH ERROR:", str(e))
        flash(f"Google login failed: {str(e)}", "error")
        return redirect(url_for("main.login"))

    email = user_info.get('email')
    
    # Check if user exists
    import secrets
    user = User.query.filter_by(email=email).first()
    
    if user:
        if not user.google_id:
            user.google_id = user_info.get('sub')
            user.provider = 'google'
            db.session.commit()
    else:
        user = User(
            email=email,
            provider='google',
            google_id=user_info.get('sub')
        )
        user.set_password(secrets.token_urlsafe(24))
        db.session.add(user)
        db.session.commit()

    login_user(user)
    flash("Successfully signed in with Google!", "success")
    return redirect(url_for('main.home'))

@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return redirect(url_for('main.register'))

        wants_newsletter = request.form.get('subscribe') is not None
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return redirect(url_for('main.register'))
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        newsletter_msg = None
        subscriber = NewsletterSubscriber.query.filter_by(email=email).first()
        if subscriber:
            subscriber.user_id = user.id
            if wants_newsletter:
                newsletter_msg = 'Your existing newsletter subscription was linked 🎯'
            else:
                newsletter_msg = 'You already have subscribed to the newsletter with this email before'
        if wants_newsletter and not subscriber:
            subscriber = NewsletterSubscriber(
                email=email,
                user_id=user.id
            )
            subscriber.generate_tokens()
            db.session.add(subscriber)

            # send confirmation email            
            send_confirmation_email(
                subscriber.email,
                subscriber.confirmation_token,
                subscriber.unsubscribe_token
            )
            # newsletter_msg = 'You\'ve been subscribed to the newsletter 📬'
            newsletter_msg = 'Check your email to confirm subscription 📬'
        db.session.commit()
        login_user(user)
        flash('Registration completed successfully 🎉', 'success')
        if newsletter_msg:
            flash(newsletter_msg, 'info')
        return redirect(url_for('main.home'))
    return render_template('register.html')

# Logout route

@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.home'))
