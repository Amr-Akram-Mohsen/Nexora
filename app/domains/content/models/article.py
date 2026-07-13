from app.core.extensions import db
from sqlalchemy.dialects.postgresql import JSONB

class Article(db.Model):
    __tablename__ = "articles"

    id = db.Column(db.Integer, primary_key=True)

    external_uri = db.Column(db.String(255), unique=True, index=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    summary = db.Column(db.Text)

    # New layered content fields
    body = db.Column(db.Text)
    content_text = db.Column(db.Text)
    content_html = db.Column(db.Text)
    word_count = db.Column(db.Integer)

    quality_score = db.Column(db.Float, default=0.0)
    
    ingestion_method = db.Column(db.String(50)) # 'diffbot', 'event_registry', 'scraper'
    language = db.Column(db.String(10), index=True)
    sentiment_score = db.Column(db.Float, index=True)
    
    authors = db.Column(db.JSON)
    extended_metadata = db.Column(
        db.JSON,
        comment=(
            "Raw provider-specific payload for debugging/auditing only. "
            "Do NOT use for routing or queries. "
            "Structured data (entities, categories, events) belongs in proper relational tables."
        )
    )
    images = db.Column(db.JSON) # Formerly extracted_images
    videos = db.Column(db.JSON)

    # Staged ingestion fields
    status = db.Column(
        db.String(20), default="discovered", index=True
    )  # discovered, enriching, ready, published, failed, archived
    last_enrichment_attempt = db.Column(db.DateTime)

    image_url = db.Column(db.Text)
    canonical_url = db.Column(db.String(500), index=True)

    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=True)
    event = db.relationship("Event", back_populates="articles")

    primary_source_id = db.Column(
        db.Integer, db.ForeignKey("article_sources.id"), nullable=True
    )
    primary_source = db.relationship(
        "ArticleSource", foreign_keys=[primary_source_id], post_update=True
    )

    # Sources where this article is published
    article_sources = db.relationship(
        "ArticleSource",
        back_populates="article",
        cascade="all, delete-orphan",
        foreign_keys="ArticleSource.article_id",
    )

    categories = db.relationship(
        "Category",
        secondary="article_categories",
        backref="articles"
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
                rel.source.authority_score if rel.source else 0,
                rel.published_at.timestamp() if rel.published_at else 0,
            ),
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
                rel.source.authority_score if rel.source else 0,
                rel.published_at.timestamp() if rel.published_at else 0,
            ),
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

        return [rel for rel in self.article_sources if rel != primary]

    @property
    def sorted_source_relations(self):
        return sorted(
            self.article_sources,
            key=lambda rel: (
                rel.source.authority_score if rel.source else 0,
                rel.published_at.timestamp() if rel.published_at else 0,
            ),
            reverse=True,
        )

    @property
    def preview_text(self):
        return self.description or (
            self.content_text[:160]
            if self.content_text
            else None
        )

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('discovered', 'enriching', 'ready', 'published', 'failed', 'archived')",
            name="ck_articles_status_valid"
        ),
    )

    def __repr__(self):
        return f"<Article {self.id} '{self.title[:30]}'>"
