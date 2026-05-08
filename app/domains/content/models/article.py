from app.core.extensions import db

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
    article_sources = db.relationship(
        "ArticleSource",
        back_populates="article",
        cascade="all, delete-orphan"
    )

    # -------- Helpers --------
    @property
    def read_time_minutes(self):
        # Use word_count if available, fallback to calculating from content_text
        if self.word_count:
            return max(1, self.word_count // 200)
        
        text = self.content_text or self.description or ""
        words = len(text.split())
        return max(1, words // 200)

    @property
    def preferred_source_relation(self):
        if not self.article_sources:
            return None

        return max(
            self.article_sources,
            key=lambda rel: (
                rel.source.authority_score or 0,
                rel.published_at.timestamp()
                if rel.published_at else 0
            )
        )
        
    @property
    def source_name(self):
        rel = self.preferred_source_relation
        return rel.source.name if rel else "Unknown"
    
    @property
    def source_url(self):
        rel = self.preferred_source_relation
        return rel.url if rel else None
    
    @property
    def alternative_source_relations(self):
        primary = self.preferred_source_relation

        return [
            rel for rel in self.article_sources
            if rel != primary
        ]

    @property
    def sorted_source_relations(self):
        return sorted(
            self.article_sources,
            key=lambda rel: (
                rel.source.authority_score or 0,
                rel.published_at.timestamp()
                if rel.published_at else 0
            ),
            reverse=True
        )


    @property
    def preview_text(self):
        return self.description or (self.content_text[:160] if self.content_text else (self.body[:160] if self.body else None))

    def __repr__(self):
        return f"<Article {self.id} '{self.title[:30]}'>"

