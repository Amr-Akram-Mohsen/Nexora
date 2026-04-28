from app.core.extensions import db

class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(300))
    body = db.Column(db.Text)

    external_id = db.Column(
        db.String(100),
        nullable=False
    )

    platform = db.Column(
        db.String(50),
        nullable=False,
        index=True
    )  # reddit, etc

    author = db.Column(db.String(100))
    subreddit = db.Column(db.String(100), index=True)

    upvotes = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)

    __table_args__ = (
        db.UniqueConstraint(
            "external_id",
            "platform",
            name="uq_posts_external_platform"
        ),
    )

    # -------- Helpers --------
    @property
    def url(self):
        if self.platform == "reddit":
            return f"https://reddit.com/comments/{self.external_id}"
        return None

    @property
    def preview_text(self):
        return self.body[:160] if self.body else None

    def __repr__(self):
        return f"<Post {self.platform}:{self.external_id}>"

