from app.core.extensions import db
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timezone

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300))
    body = db.Column(db.Text)
    external_id = db.Column(db.String(100), nullable=False)
    platform = db.Column(db.String(50), nullable=False, index=True)
    author = db.Column(db.String(100))
    upvotes = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    community = db.Column(db.String(150), index=True)
    url = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    platform_metadata = db.Column(JSONB, nullable=True)
    thumbnail_url = db.Column(db.Text, nullable=True)
    __table_args__ = (db.UniqueConstraint('external_id', 'platform', name='uq_posts_external_platform'), db.Index('ix_posts_platform_created_at', 'platform', 'created_at'), db.Index('ix_posts_platform_community', 'platform', 'community'))

    @property
    def preview_text(self):
        return self.body[:160] if self.body else None

    def __repr__(self):
        return f'<Post {self.platform}:{self.external_id}>'