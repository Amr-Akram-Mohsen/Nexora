from app.core.extensions import db

# ==================== ASSOCIATION TABLES ====================
article_sections = db.Table(
    "article_sections",
    db.Column("article_id", db.Integer, db.ForeignKey(
        "articles.id"), primary_key=True),
    db.Column("section_id", db.Integer, db.ForeignKey(
        "sections.id"), primary_key=True)
)

article_topics = db.Table(
    "article_topics",
    db.Column("article_id", db.Integer, db.ForeignKey("articles.id"), primary_key=True),
    db.Column("topic_id", db.Integer, db.ForeignKey("topics.id"), primary_key=True)
)

article_brands = db.Table(
    "article_brands",
    db.Column("article_id", db.Integer, db.ForeignKey(
        "articles.id"), primary_key=True),
    db.Column("brand_id", db.Integer, db.ForeignKey(
        "brands.id"), primary_key=True)
)

item_sections = db.Table(
    "item_sections",
    db.Column("item_id", db.Integer, db.ForeignKey(
        "items.id"), primary_key=True),
    db.Column("section_id", db.Integer, db.ForeignKey(
        "sections.id"), primary_key=True)
)

item_topics = db.Table(
    "item_topics",
    db.Column("item_id", db.Integer, db.ForeignKey("items.id"), primary_key=True),
    db.Column("topic_id", db.Integer, db.ForeignKey("topics.id"), primary_key=True)
)

# Links a review/article directly to the product(s) it covers
article_items = db.Table(
    "article_items",
    db.Column("article_id", db.Integer, db.ForeignKey("articles.id"), primary_key=True),
    db.Column("item_id",    db.Integer, db.ForeignKey("items.id"),    primary_key=True)
)

