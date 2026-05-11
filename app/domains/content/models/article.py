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
    
    # Staged ingestion fields
    status = db.Column(db.String(20), default="pending", index=True)  # pending, enriching, complete, failed
    last_enrichment_attempt = db.Column(db.DateTime)
    
    body = db.Column(db.Text)  # Keep for migration
    image_url = db.Column(db.Text)
    canonical_url = db.Column(db.String(500), index=True)
    
    primary_source_id = db.Column(db.Integer, db.ForeignKey("article_sources.id"), nullable=True)
    primary_source = db.relationship(
        "ArticleSource",
        foreign_keys=[primary_source_id],
        post_update=True
    )

    # Sources where this article is published
    article_sources = db.relationship(
        "ArticleSource",
        back_populates="article",
        cascade="all, delete-orphan",
        foreign_keys="ArticleSource.article_id"
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

    def update_primary_source(self):
        """Recalculates the primary source based on authority and date."""
        if not self.article_sources:
            self.primary_source_id = None
            return

        best = max(
            self.article_sources,
            key=lambda rel: (
                rel.source.authority_score or 0,
                rel.published_at.timestamp()
                if rel.published_at else 0
            )
        )
        self.primary_source_id = best.id

    @property
    def preferred_source_relation(self):
        # Use materialized primary_source if available for speed
        if self.primary_source:
            return self.primary_source
            
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
    def url(self):
        return self.source_url
    
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

