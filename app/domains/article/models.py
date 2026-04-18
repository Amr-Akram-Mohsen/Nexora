from datetime import datetime, timezone
from app.core.extensions import db
from app.domains.core.relationships import (article_sections, article_topics, article_brands, article_items)

class Article(db.Model):
    __tablename__ = "articles"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text)
    url = db.Column(db.Text, nullable=False, unique=True)
    source_id = db.Column(db.String(120))
    source_name = db.Column(db.String(200))
    published_at = db.Column(db.DateTime)
    retrieved_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    image_url = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    comment_count = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)
    card_type = db.Column(db.TEXT, default="article")
    # Tracker for matcher — set to utcnow() after each matching run
    last_matched_at = db.Column(db.DateTime, nullable=True, index=True)
    importance_score = db.Column(db.Float, default=0, index=True)
    enhanced_query = db.Column(db.Text)

    topics = db.relationship("Topic", secondary=article_topics, back_populates="articles")
    sections = db.relationship("Section", secondary=article_sections, back_populates="articles")
    brands = db.relationship("Brand", secondary=article_brands, back_populates="articles")
    
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    category = db.relationship("Category", back_populates="articles")
    
    # Products this article reviews / mentions
    linked_items = db.relationship(
        "Item",
        secondary=article_items,
        back_populates="linked_articles"
    )
    
    # Reactions, Comments, Views
    reactions = db.relationship(
        "Reaction",
        primaryjoin="and_(foreign(Reaction.target_id)==Article.id, Reaction.target_type=='article')",
        back_populates="article",
        viewonly=True,
        lazy="selectin"
    )
    comments = db.relationship(
        "Comment",
        primaryjoin="and_(foreign(Comment.target_id)==Article.id, Comment.target_type=='article')",
        back_populates="article",
        viewonly=True,
        lazy="selectin"
    )
    views = db.relationship(
        "View",
        primaryjoin="and_(foreign(View.target_id)==Article.id, View.target_type=='article')",
        back_populates="article",
        viewonly=True,
        lazy="selectin"
    )

    __table_args__ = (
        db.Index("idx_published_at", "published_at"),
        db.Index("idx_article_category_published", "category_id", "published_at"),
        db.Index("idx_article_active", "is_active"),
        db.Index("idx_article_views", "view_count"),
        db.Index("idx_article_active_published", "is_active", "published_at"),

        db.Index("ix_article_category_active_published",
                "category_id", "is_active", "published_at"),

        db.Index("ix_article_brand_lookup",
                "id", "is_active", "importance_score"),
        db.UniqueConstraint('source_name', 'title', name='uq_articles_source_title'),
    )

    @property
    def read_time_minutes(self):
        from sqlalchemy.orm.attributes import instance_state
        state = instance_state(self)
        if 'content' not in state.unloaded and self.content:
            text = self.content
        else:
            text = self.description or ""
            
        words = len(text.split())
        return max(1, words // 200)

    def __repr__(self):
        return f"<Article {self.title[:60]}>"

    # ---------------- Convenience helpers ----------------
    def add_section(self, section_obj):
        if section_obj not in self.sections:
            self.sections.append(section_obj)
    def add_brand(self, brand_obj):
        if brand_obj not in self.brands:
            self.brands.append(brand_obj)
    def add_topic(self, topic_obj):
        if topic_obj not in self.topics:
            self.topics.append(topic_obj)
    def link_item(self, item_obj):
        if item_obj not in self.linked_items:
            self.linked_items.append(item_obj)


