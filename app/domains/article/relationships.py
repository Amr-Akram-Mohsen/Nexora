from app.core.extensions import db

# ==================== ASSOCIATION TABLES ====================
article_sections = db.Table(
    "article_sections",
    db.Column("article_id", db.Integer, db.ForeignKey(
        "articles.id"), primary_key=True),
    db.Column("section_id", db.Integer, db.ForeignKey(
        "sections.id"), primary_key=True),

    db.Index("ix_article_sections_section", "section_id"),
    db.Index("ix_article_sections_article", "article_id"),
)

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

item_sections = db.Table(
    "item_sections",
    db.Column("item_id", db.Integer, db.ForeignKey(
        "items.id"), primary_key=True),
    db.Column("section_id", db.Integer, db.ForeignKey(
        "sections.id"), primary_key=True),

    db.Index("ix_item_sections_section", "section_id"),
    db.Index("ix_item_sections_item", "item_id"),
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

