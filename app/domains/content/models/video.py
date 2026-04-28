from app.core.extensions import db

class Video(db.Model):
    __tablename__ = "videos"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)

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

    __table_args__ = (
        db.UniqueConstraint(
            "external_id",
            "platform",
            name="uq_videos_external_platform"
        ),
    )

    # -------- Helpers --------
    @property
    def url(self):
        if self.platform == "youtube":
            return f"https://www.youtube.com/watch?v={self.external_id}"
        return None

    @property
    def preview_text(self):
        return self.description

    def __repr__(self):
        return f"<Video {self.platform}:{self.external_id}>"

