from app.core.extensions import db
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timezone

class Video(db.Model):
    __tablename__ = "videos"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    description_display_rule = db.Column(db.String(20), default='review', nullable=False)

    external_id = db.Column(
        db.String(100),
        nullable=False
    )

    platform = db.Column(
        db.String(50),
        nullable=False,
        index=True
    )  # youtube, vimeo...

    thumbnail_url = db.Column(db.Text)
    channel_name = db.Column(db.String(150))

    url = db.Column(
        db.Text,
        nullable=True
    )

    creator = db.Column(
        db.String(150)
    )

    published_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    duration_seconds = db.Column(
        db.Integer
    )

    view_count = db.Column(
        db.BigInteger,
        nullable=False,
        default=0
    )

    like_count = db.Column(
        db.BigInteger,
        nullable=False,
        default=0
    )

    comments_count = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    video_comments = db.relationship(
        "VideoComment",
        backref="video",
        cascade="all, delete-orphan",
        order_by="desc(VideoComment.like_count)"
    )

    platform_metadata = db.Column(
        JSONB,
        nullable=True
    )

    __table_args__ = (
        db.UniqueConstraint(
            "external_id",
            "platform",
            name="uq_videos_external_platform"
        ),

        db.Index(
            "ix_videos_platform_published",
            "platform",
            "published_at"
        ),

        db.Index(
            "ix_videos_platform_creator",
            "platform",
            "creator"
        ),

    )

    # -------- Helpers --------
    @property
    def preview_text(self):
        return self.description

    def __repr__(self):
        return f"<Video {self.platform}:{self.external_id}>"


class VideoComment(db.Model):
    __tablename__ = "video_comments"

    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    
    external_id = db.Column(db.String(100), nullable=False, unique=True, index=True)
    
    author_name = db.Column(db.String(150))
    author_channel_id = db.Column(db.String(100))
    
    text = db.Column(db.Text, nullable=False)
    
    like_count = db.Column(db.Integer, nullable=False, default=0)
    reply_count = db.Column(db.Integer, nullable=False, default=0)
    
    published_at = db.Column(db.DateTime, index=True)
    updated_at = db.Column(db.DateTime)

    def __repr__(self):
        return f"<VideoComment {self.external_id}>"

