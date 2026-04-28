from app.core.extensions import db

# ==================== ASSOCIATION TABLES ====================

content_topics = db.Table(
    "content_topics",
    db.Column("content_id", db.Integer, db.ForeignKey("contents.id"), primary_key=True),
    db.Column("topic_id", db.Integer, db.ForeignKey("topics.id"), primary_key=True),

    db.Index("ix_content_topics_topic", "topic_id"),
    db.Index("ix_content_topics_content", "content_id"),
)

content_brands = db.Table(
    "content_brands",
    db.Column("content_id", db.Integer, db.ForeignKey(
        "contents.id"), primary_key=True),
    db.Column("brand_id", db.Integer, db.ForeignKey(
        "brands.id"), primary_key=True),

    db.Index("ix_content_brands_brand", "brand_id"),
    db.Index("ix_content_brands_content", "content_id"),
)

item_topics = db.Table(
    "item_topics",
    db.Column("item_id", db.Integer, db.ForeignKey("items.id"), primary_key=True),
    db.Column("topic_id", db.Integer, db.ForeignKey("topics.id"), primary_key=True),

    db.Index("ix_item_topics_topic", "topic_id"),
    db.Index("ix_item_topics_item", "item_id"),
)

# Links a review/content directly to the product(s) it covers
content_items = db.Table(
    "content_items",
    db.Column("content_id", db.Integer, db.ForeignKey("contents.id"), primary_key=True),
    db.Column("item_id",    db.Integer, db.ForeignKey("items.id"),    primary_key=True)
)


content_attributes = db.Table(
    "content_attributes",
    db.Column("content_id", db.Integer, db.ForeignKey("contents.id"), primary_key=True),
    db.Column("attribute_id", db.Integer, db.ForeignKey("attributes.id"), primary_key=True),

    db.Index("ix_content_attributes_attribute", "attribute_id"),
    db.Index("ix_content_attributes_content", "content_id")
)

# Links an article to multiple sources (The Verge, Wired, etc.)
article_sources = db.Table(
    "article_sources",
    db.Column("article_id", db.Integer, db.ForeignKey("articles.id"), primary_key=True),
    db.Column("source_id",  db.Integer, db.ForeignKey("sources.id"),  primary_key=True),
    db.Column("url",        db.Text,    nullable=False), # Specific URL for this source

    db.Index("ix_article_sources_source", "source_id"),
    db.Index("ix_article_sources_article", "article_id"),
)
