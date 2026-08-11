from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime, timezone
import secrets
from app.core.extensions import db

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.Text, nullable=False)
    google_id = db.Column(db.Text, unique=True, nullable=True)
    provider = db.Column(db.Text, nullable=True)  # 'google' or 'local'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)

    verified_at = db.Column(db.DateTime(timezone=True), nullable=True)

    verification_sent_at = db.Column(db.DateTime(timezone=True), nullable=True)

    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)

    password_changed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    newsletter_subscription = db.relationship(
        "NewsletterSubscriber",
        back_populates="user",
        uselist=False
    )
    reactions = db.relationship("Reaction", back_populates="user", cascade="all, delete-orphan")
    comments = db.relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    views = db.relationship("View", back_populates="user", cascade="all, delete-orphan")
    saves = db.relationship(
        "Save",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    shares = db.relationship(
        "Share",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    user_interests = db.relationship(
        "UserInterest",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    product_clicks = db.relationship("ProductClick", back_populates="user")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    __table_args__ = (
        db.CheckConstraint(
            "(google_id IS NULL AND provider IS NULL) OR (google_id IS NOT NULL AND provider IS NOT NULL)",
            name="ck_google_user"
        ),
    )

    def __repr__(self):
        return f'<User {self.email}>'

class NewsletterSubscriber(db.Model):
    __tablename__ = 'newsletter_subscribers'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    is_confirmed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    unsubscribed_at = db.Column(db.DateTime, nullable=True)
    confirmation_token = db.Column(db.String(255), nullable=True)
    unsubscribe_token = db.Column(db.String(255), nullable=True)    
    user = db.relationship("User", back_populates="newsletter_subscription")

    def generate_tokens(self):
        self.confirmation_token = secrets.token_urlsafe(32)
        self.unsubscribe_token = secrets.token_urlsafe(32)

    @property
    def is_active(self):
        return self.is_confirmed and self.unsubscribed_at is None
        
    def __repr__(self):
        return f'<NewsletterSubscriber {self.email}>'

class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
