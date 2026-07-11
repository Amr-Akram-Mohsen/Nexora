from app.core.extensions import db

# ==================== ASSOCIATION TABLES ====================

content_locations = db.Table(
    "content_locations",
    db.Column("content_id", db.Integer, db.ForeignKey("contents.id"), primary_key=True),
    db.Column("location_id", db.Integer, db.ForeignKey("locations.id"), primary_key=True),
    db.Index("ix_content_locations_location", "location_id"),
    db.Index("ix_content_locations_content", "content_id"),
)

article_categories = db.Table(
    "article_categories",
    db.Column("article_id", db.Integer, db.ForeignKey("articles.id"), primary_key=True),
    db.Column("category_id", db.Integer, db.ForeignKey("categories.id"), primary_key=True),
    db.Index("ix_article_categories_category", "category_id"),
    db.Index("ix_article_categories_article", "article_id"),
)

class ContentEntity(db.Model):
    __tablename__ = "content_entities"
    content_id = db.Column(db.Integer, db.ForeignKey("contents.id"), primary_key=True)
    entity_id = db.Column(db.Integer, db.ForeignKey("entities.id"), primary_key=True)
    relevance_score = db.Column(db.Float, default=0.0)
    
    # NEW fields
    origin = db.Column(db.String(30), nullable=True, index=True)
    # Values: 'event_registry' | 'diffbot' | 'youtube' | 'brand_legacy' | 'manual' | 'ai'
    confidence = db.Column(db.Float, nullable=True)
    # Provider-assigned confidence (0.0–1.0), NULL if unknown
    
    content = db.relationship("Content", back_populates="content_entities")
    entity = db.relationship("Entity", back_populates="content_entities")

    @staticmethod
    def get_or_create(content_id, entity_id, session, origin=None, relevance_score=0.0, confidence=None):
        """Get existing link or create new one. Updates origin if provided."""
        existing = session.query(ContentEntity).filter_by(
            content_id=content_id, entity_id=entity_id
        ).first()
        if not existing:
            existing = ContentEntity(
                content_id=content_id,
                entity_id=entity_id,
                relevance_score=relevance_score,
                origin=origin,
                confidence=confidence,
            )
            session.add(existing)
            session.flush()
        return existing



# Links a review/content directly to the product(s) it covers
content_products = db.Table(
    "content_products",
    db.Column("content_id", db.Integer, db.ForeignKey("contents.id"), primary_key=True),
    db.Column("product_id", db.Integer, db.ForeignKey("products.id"), primary_key=True),
    db.Index("ix_content_products_content", "content_id"),
    db.Index("ix_content_products_product", "product_id"),
)


content_attributes = db.Table(
    "content_attributes",
    db.Column("content_id", db.Integer, db.ForeignKey("contents.id"), primary_key=True),
    db.Column(
        "attribute_id", db.Integer, db.ForeignKey("attributes.id"), primary_key=True
    ),
    db.Index("ix_content_attributes_attribute", "attribute_id"),
    db.Index("ix_content_attributes_content", "content_id"),
)

class ArticleSource(db.Model):
    __tablename__ = "article_sources"

    id = db.Column(db.Integer, primary_key=True)

    article_id = db.Column(db.Integer, db.ForeignKey("articles.id"), nullable=False)

    source_id = db.Column(db.Integer, db.ForeignKey("sources.id"), nullable=False)

    url = db.Column(db.Text, unique=True, nullable=False)

    published_at = db.Column(db.DateTime, nullable=True, index=True)

    article = db.relationship(
        "Article", back_populates="article_sources", foreign_keys=[article_id]
    )

    source = db.relationship("Source", back_populates="article_sources")

