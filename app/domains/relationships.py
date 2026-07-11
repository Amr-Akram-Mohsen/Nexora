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
    
    content = db.relationship("Content", back_populates="content_entities")
    entity = db.relationship("Entity", back_populates="content_entities")

content_topics = db.Table(
    "content_topics",
    db.Column("content_id", db.Integer, db.ForeignKey("contents.id"), primary_key=True),
    db.Column("topic_id", db.Integer, db.ForeignKey("topics.id"), primary_key=True),
    db.Index("ix_content_topics_topic", "topic_id"),
    db.Index("ix_content_topics_content", "content_id"),
)

content_brands = db.Table(
    "content_brands",
    db.Column("content_id", db.Integer, db.ForeignKey("contents.id"), primary_key=True),
    db.Column("brand_id", db.Integer, db.ForeignKey("brands.id"), primary_key=True),
    db.Index("ix_content_brands_brand", "brand_id"),
    db.Index("ix_content_brands_content", "content_id"),
)

# Links a review/content directly to the product(s) it covers
content_items = db.Table(
    "content_items",
    db.Column("content_id", db.Integer, db.ForeignKey("contents.id"), primary_key=True),
    db.Column("item_id", db.Integer, db.ForeignKey("items.id"), primary_key=True),
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

