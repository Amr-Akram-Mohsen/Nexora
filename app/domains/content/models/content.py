from datetime import datetime, timezone
from app.core.extensions import db
from app.domains.relationships import (content_topics, content_brands, content_items, content_attributes)
from sqlalchemy.orm import object_session

class Content(db.Model):
    __tablename__ = "contents"

    id = db.Column(db.Integer, primary_key=True)

    object_type = db.Column(
        db.String(20),
        nullable=False,
        index=True  # for fast filtering (feed queries)
    )  # 'article' | 'video' | 'post'

    object_id = db.Column(
        db.Integer,
        nullable=False,
        index=True
    )

    published_at = db.Column(
        db.DateTime,
        nullable=False,
        index=True
    )

    ingested_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    is_active = db.Column(db.Boolean, default=True)
    is_published = db.Column(db.Boolean, default=False, index=True)
    comment_count = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)
    

    # Optional (future-proofing)
    score = db.Column(db.Float, default=0.0, index=True)
    
    # Optional (future-proofing)
    review_score = db.Column(db.Float, default=0.0, index=True)
    
    # Optional (future-proofing)
    review_count = db.Column(db.Integer, default=0, index=True)

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=False)

    gender_id = db.Column(db.Integer, db.ForeignKey("gender_facets.id"))
    intent_id = db.Column(db.Integer, db.ForeignKey("intent_facets.id"))
    price_tier_id = db.Column(db.Integer, db.ForeignKey("price_tier_facets.id"))

    category = db.relationship("Category", back_populates="contents")
    section = db.relationship("Section", back_populates="contents")

    gender = db.relationship("GenderFacet", back_populates="contents")
    intent = db.relationship("IntentFacet", back_populates="contents")
    price_tier = db.relationship("PriceTierFacet", back_populates="contents")


    topics = db.relationship("Topic", secondary=content_topics, back_populates="contents")
    brands = db.relationship("Brand", secondary=content_brands, back_populates="contents")
    attributes = db.relationship(
        "AttributeFacet",
        secondary=content_attributes,
        back_populates="contents"
    )
    
    # Products this content reviews / mentions
    linked_items = db.relationship(
        "Item",
        secondary=content_items,
        back_populates="linked_contents"
    )

    # Reactions, Comments, Views
    reactions = db.relationship(
        "Reaction",
        primaryjoin="and_(foreign(Reaction.target_id)==Content.id, Reaction.target_type=='content')",
        back_populates="content",
        viewonly=True,
        lazy="selectin"
    )
    comments = db.relationship(
        "Comment",
        primaryjoin="and_(foreign(Comment.target_id)==Content.id, Comment.target_type=='content')",
        back_populates="content",
        viewonly=True,
        lazy="selectin"
    )
    views = db.relationship(
        "View",
        primaryjoin="and_(foreign(View.target_id)==Content.id, View.target_type=='content')",
        back_populates="content",
        viewonly=True,
        lazy="selectin"
    )


    __table_args__ = (
        db.Index("ix_contents_published_at", "published_at"),
        db.Index("ix_contents_active", "is_active"),
        db.Index("ix_contents_view_count", "view_count"),

        db.Index("ix_contents_score", "score"),
        db.Index("ix_contents_review_score", "review_score"),
        db.Index("ix_contents_review_count", "review_count"),

        # Core filters
        db.Index("ix_contents_section_id", "section_id"),
        db.Index("ix_contents_category_id", "category_id"),

        # Feed queries
        db.Index("ix_contents_category_published_at", "category_id", "published_at"),

        # Facets
        db.Index("ix_contents_gender_id", "gender_id"),
        db.Index("ix_contents_intent_id", "intent_id"),
        db.Index("ix_contents_price_tier_id", "price_tier_id"),

        # Advanced filtering
        db.Index("ix_contents_category_intent_published_at",
            "category_id", "intent_id", "published_at"),
        db.Index("ix_contents_section_published_at",
            "section_id", "published_at"),
        db.Index("ix_contents_active_published_at", "is_active", "published_at"),

        db.UniqueConstraint(
            "object_type",
            "object_id",
            name="uq_contents_object_type_id"
        ),
        db.CheckConstraint(
            "object_type IN ('article', 'video', 'post')",
            name="ck_contents_object_type_valid"
        ),
        
    )

    # -------- Helper --------
    # @property
    # def target(self):
    #     session = object_session(self)
    #     if not session:
    #         return None
    #     return resolve_content_object(session, self)

    # @property
    # def title(self):
    #     return getattr(self.target, "title", None)

    # @property
    # def preview_text(self):
    #     return getattr(self.target, "preview_text", None)

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

    def __repr__(self):
        return f"<Content {self.object_type}:{self.object_id}>"

