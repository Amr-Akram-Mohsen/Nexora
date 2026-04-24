from app.core.extensions import db

# ==================== ASSOCIATION TABLES ====================

article_topics = db.Table(
    "article_topics",
    db.Column("article_id", db.Integer, db.ForeignKey("articles.id"), primary_key=True),
    db.Column("topic_id", db.Integer, db.ForeignKey("topics.id"), primary_key=True),

    db.Index("ix_article_topics_topic", "topic_id"),
    db.Index("ix_article_topics_article", "article_id"),
)

article_brands = db.Table(
    "article_brands",
    db.Column("article_id", db.Integer, db.ForeignKey(
        "articles.id"), primary_key=True),
    db.Column("brand_id", db.Integer, db.ForeignKey(
        "brands.id"), primary_key=True),

    db.Index("ix_article_brands_brand", "brand_id"),
    db.Index("ix_article_brands_article", "article_id"),
)

item_topics = db.Table(
    "item_topics",
    db.Column("item_id", db.Integer, db.ForeignKey("items.id"), primary_key=True),
    db.Column("topic_id", db.Integer, db.ForeignKey("topics.id"), primary_key=True),

    db.Index("ix_item_topics_topic", "topic_id"),
    db.Index("ix_item_topics_item", "item_id"),
)

# Links a review/article directly to the product(s) it covers
article_items = db.Table(
    "article_items",
    db.Column("article_id", db.Integer, db.ForeignKey("articles.id"), primary_key=True),
    db.Column("item_id",    db.Integer, db.ForeignKey("items.id"),    primary_key=True)
)


article_attributes = db.Table(
    "article_attributes",
    db.Column("article_id", db.Integer, db.ForeignKey("articles.id"), primary_key=True),
    db.Column("attribute_id", db.Integer, db.ForeignKey("attributes.id"), primary_key=True),

    db.Index("ix_article_attributes_attribute", "attribute_id"),
    db.Index("ix_article_attributes_article", "article_id")
)
