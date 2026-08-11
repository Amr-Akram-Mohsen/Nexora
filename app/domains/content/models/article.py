from app.core.extensions import db
from sqlalchemy.dialects.postgresql import JSONB
from app.domains.relationships import ArticleCategory

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    summary = db.Column(db.Text)
    body = db.Column(db.Text)
    content_text = db.Column(db.Text)
    content_html = db.Column(db.Text)
    word_count = db.Column(db.Integer)
    quality_score = db.Column(db.Float, default=0.0, nullable=False)
    enrichment_priority = db.Column(db.Float, default=0.0, nullable=False, index=True, comment='Priority score for enrichment worker. Calculated before enrichment.')
    ingestion_method = db.Column(db.String(50))
    language = db.Column(db.String(10), index=True)
    sentiment_score = db.Column(db.Float, index=True)
    authors = db.relationship('Author', secondary='article_authors', backref='article_rels')
    extended_metadata = db.Column(db.JSON, comment='Raw provider-specific payload for debugging/auditing only. Do NOT use for routing or queries. Structured data (entities, categories, events) belongs in proper relational tables.')
    images = db.Column(db.JSON)
    videos = db.Column(db.JSON)
    status = db.Column(db.String(20), default='discovered', index=True)
    last_enrichment_attempt = db.Column(db.DateTime)
    image_url = db.Column(db.Text)
    canonical_url = db.Column(db.String(500), index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=True)
    event = db.relationship('Event', back_populates='articles')
    primary_source_id = db.Column(db.Integer, db.ForeignKey('article_sources.id'), nullable=True)
    primary_source = db.relationship('ArticleSource', foreign_keys=[primary_source_id], post_update=True)
    article_sources = db.relationship('ArticleSource', back_populates='article', cascade='all, delete-orphan', foreign_keys='ArticleSource.article_id')
    category_associations = db.relationship('ArticleCategory', back_populates='article', cascade='all, delete-orphan')
    from sqlalchemy.ext.associationproxy import association_proxy
    categories = association_proxy('category_associations', 'category', creator=lambda c: ArticleCategory(category=c))

    @property
    def is_content_scraped(self):
        return self.status in ('ready', 'published', 'complete') or bool(self.content_html)

    @property
    def read_time_minutes(self):
        if self.word_count:
            return max(1, self.word_count // 200)
        text = self.content_text or self.description or ''
        words = len(text.split())
        return max(1, words // 200)

    def update_primary_source(self):
        if not self.article_sources:
            self.primary_source_id = None
            return
        best = max(self.article_sources, key=lambda rel: (rel.source.authority_score if rel.source else 0, rel.published_at.timestamp() if rel.published_at else 0))
        self.primary_source_id = best.id

    @property
    def preferred_source(self):
        if self.primary_source:
            return self.primary_source
        if not self.article_sources:
            return None
        return max(self.article_sources, key=lambda rel: (rel.source.authority_score if rel.source else 0, rel.published_at.timestamp() if rel.published_at else 0))

    @property
    def source_name(self):
        rel = self.preferred_source
        return rel.source.name if rel else 'Unknown'

    @property
    def source_url(self):
        rel = self.preferred_source
        return rel.url if rel else None

    @property
    def url(self):
        return self.source_url

    @property
    def alternative_source_relations(self):
        primary = self.preferred_source
        return [rel for rel in self.article_sources if rel != primary]

    @property
    def sorted_source_relations(self):
        return sorted(self.article_sources, key=lambda rel: (rel.source.authority_score if rel.source else 0, rel.published_at.timestamp() if rel.published_at else 0), reverse=True)

    @property
    def preview_text(self):
        return self.description or (self.content_text[:160] if self.content_text else None)
    __table_args__ = (db.CheckConstraint("status IN ('discovered', 'enriching', 'ready', 'published', 'failed', 'archived')", name='ck_articles_status_valid'),)

    def __repr__(self):
        return f"<Article {self.id} '{self.title[:30]}'>"