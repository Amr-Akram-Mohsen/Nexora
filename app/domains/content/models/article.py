from app.core.extensions import db
from app.domains.relationships import article_sources

class Article(db.Model):
    __tablename__ = "articles"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    
    # New layered content fields
    content_text = db.Column(db.Text)
    content_html = db.Column(db.Text)
    word_count = db.Column(db.Integer)
    
    quality_score = db.Column(db.Float, default=0.0)
    is_content_scraped = db.Column(db.Boolean, default=False)
    content_source = db.Column(db.String(50))
    
    body = db.Column(db.Text)  # Keep for migration
    image_url = db.Column(db.Text)

    # Sources where this article is published
    sources = db.relationship(
        "Source",
        secondary=article_sources,
        back_populates="articles"
    )
    
    # -------- Helpers --------
    @property
    def source_name(self):
        if self.sources:
            return self.sources[0].name
        return 'Unknown'
    
    @property
    def read_time_minutes(self):
        # Use word_count if available, fallback to calculating from content_text
        if self.word_count:
            return max(1, self.word_count // 200)
        
        text = self.content_text or self.description or ""
        words = len(text.split())
        return max(1, words // 200)

    @property
    def url(self):
        from sqlalchemy.orm import object_session
        session = object_session(self)
        if not session:
            return None
        from app.domains.relationships import article_sources
        res = session.query(article_sources.c.url).filter(article_sources.c.article_id == self.id).first()
        return res[0] if res else None

    @property
    def preview_text(self):
        return self.description or (self.content_text[:160] if self.content_text else (self.body[:160] if self.body else None))

    def __repr__(self):
        return f"<Article {self.id} '{self.title[:30]}'>"

