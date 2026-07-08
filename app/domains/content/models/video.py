from app.core.extensions import db
from sqlalchemy.dialects.postgresql import JSONB

class Video(db.Model):
    __tablename__ = "videos"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    description_display_rule = db.Column(db.String(20), default='review')

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
        default=0
    )

    like_count = db.Column(
        db.BigInteger,
        default=0
    )

    comments_count = db.Column(
        db.Integer,
        default=0
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

