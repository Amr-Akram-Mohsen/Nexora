from datetime import datetime, timezone
from app.core.extensions import db
from app.domains.relationships import (article_topics, article_brands, article_items, article_attributes, article_sources)

from sqlalchemy.dialects.postgresql import JSONB

class Article(db.Model):
    __tablename__ = "articles"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text)
    url = db.Column(db.Text, nullable=False, unique=True)
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
    is_content_scraped = db.Column(db.Boolean, default=False, index=True)

    gender_id = db.Column(db.Integer, db.ForeignKey("gender_facets.id"))
    intent_id = db.Column(db.Integer, db.ForeignKey("intent_facets.id"))
    price_tier_id = db.Column(db.Integer, db.ForeignKey("price_tier_facets.id"))

    gender = db.relationship("GenderFacet", back_populates="articles")
    intent = db.relationship("IntentFacet", back_populates="articles")
    price_tier = db.relationship("PriceTierFacet", back_populates="articles")

    attributes = db.relationship(
        "AttributeFacet",
        secondary=article_attributes,
        back_populates="articles"
    )


    topics = db.relationship("Topic", secondary=article_topics, back_populates="articles")
    brands = db.relationship("Brand", secondary=article_brands, back_populates="articles")
    
    extra_metadata = db.Column(JSONB, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=False)

    category = db.relationship("Category", back_populates="articles")
    section = db.relationship("Section", back_populates="articles")
    
    # Products this article reviews / mentions
    linked_items = db.relationship(
        "Item",
        secondary=article_items,
        back_populates="linked_articles"
    )

    # Sources where this article is published
    sources = db.relationship(
        "Source",
        secondary=article_sources,
        back_populates="articles"
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

    @classmethod
    def exists(cls, url: str) -> bool:
        """Check if an article with the given URL exists in the database."""
        if not url:
            return False
        return db.session.query(cls.id).filter_by(url=url).first() is not None

    @staticmethod
    def get_by_url(url, session):
        return session.query(Article).filter_by(url=url).first()


    __table_args__ = (
        # Core filters
        db.Index("idx_published_at", "published_at"),
        db.Index("idx_article_active", "is_active"),
        db.Index("idx_article_views", "view_count"),

        db.Index("ix_article_importance", "importance_score"),

        # Core filters
        db.Index("ix_articles_section", "section_id"),
        db.Index("ix_articles_category", "category_id"),
        
        # Feed queries
        db.Index("idx_article_category_published", "category_id", "published_at"),

        # Facets
        db.Index("ix_articles_gender", "gender_id"),
        db.Index("ix_articles_intent", "intent_id"),
        db.Index("ix_articles_price_tier", "price_tier_id"),

        # Advanced filtering
        db.Index("ix_articles_category_intent_date",
            "category_id", "intent_id", "published_at"),
        db.Index("ix_articles_section_date",
            "section_id", "published_at"),
        db.Index("ix_articles_active_published", "is_active", "published_at"),
        db.Index("ix_articles_content_status", "is_content_scraped", "is_active"),
    )

    @property
    def source_name(self) -> str:
        """
        Backward-compatible property.
        Returns the name of the first linked Source, or the URL hostname as fallback.
        Replaces the old `source_name` string column that was removed in the schema refactor.
        """
        if self.sources:
            return self.sources[0].name
        # Graceful fallback: extract hostname from the article URL
        if self.url:
            try:
                from urllib.parse import urlparse
                return urlparse(self.url).netloc or "Unknown"
            except Exception:
                pass
        return "Unknown"

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
    def add_brand(self, brand_obj):
        if brand_obj not in self.brands:
            self.brands.append(brand_obj)
    def add_topic(self, topic_obj):
        if topic_obj not in self.topics:
            self.topics.append(topic_obj)
    def link_item(self, item_obj):
        if item_obj not in self.linked_items:
            self.linked_items.append(item_obj)

    def add_attribute(self, attr_obj):
        if attr_obj not in self.attributes:
            self.attributes.append(attr_obj)

    def add_source(self, source_obj, url: str):
        """Add a source to the article. If the source is already linked, does nothing."""
        # Check if already linked to this source
        if source_obj not in self.sources:
            # We use the association table directly to store the specific URL
            ins = article_sources.insert().values(
                article_id=self.id,
                source_id=source_obj.id,
                url=url
            )
            db.session.execute(ins)
