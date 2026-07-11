from datetime import datetime, timezone
from app.core.extensions import db

class DistributionPlatform(db.Model):
    __tablename__ = "distribution_platforms"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False) # e.g. "youtube", "pinterest", "instagram", "facebook"
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    posts = db.relationship("DistributionPost", back_populates="platform", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DistributionPlatform {self.name}>"

class DistributionPost(db.Model):
    __tablename__ = "distribution_posts"
    id = db.Column(db.Integer, primary_key=True)
    platform_id = db.Column(db.Integer, db.ForeignKey("distribution_platforms.id", ondelete="CASCADE"), nullable=False)
    
    # Generic target to point to a Nexora Asset (Content or Product)
    source_target_type = db.Column(db.String(50), nullable=False) # 'content' or 'product'
    source_target_id = db.Column(db.Integer, nullable=False)
    
    status = db.Column(db.String(20), default="draft", index=True) # "draft", "scheduled", "published"
    
    platform_specific_text = db.Column(db.Text, nullable=True) # Caption, description, or script
    external_url = db.Column(db.Text, nullable=True) # Link to the live post on the social network
    
    publish_date = db.Column(db.DateTime, nullable=True, index=True) # Target or actual publish date
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Performance metrics (initially manual, designed for future API sync)
    views_count = db.Column(db.Integer, default=0)
    likes_count = db.Column(db.Integer, default=0)
    clicks_count = db.Column(db.Integer, default=0)
    shares_count = db.Column(db.Integer, default=0)

    platform = db.relationship("DistributionPlatform", back_populates="posts")
    
    # Optional relationships to link back to the source objects for easy access
    content_target = db.relationship(
        "Content",
        primaryjoin="and_(foreign(DistributionPost.source_target_id) == Content.id, DistributionPost.source_target_type == 'content')",
        viewonly=True,
        lazy="selectin"
    )
    item_target = db.relationship(
        "Product",
        primaryjoin="and_(foreign(DistributionPost.source_target_id) == Product.id, DistributionPost.source_target_type == 'product')",
        viewonly=True,
        lazy="selectin"
    )

    @property
    def source(self):
        return self.content_target or self.item_target

    __table_args__ = (
        db.Index("ix_distribution_post_target", "source_target_type", "source_target_id"),
        db.CheckConstraint("source_target_type IN ('content', 'product')", name="ck_distribution_post_target_type"),
    )

    def __repr__(self):
        return f"<DistributionPost {self.id} on {self.platform.name if self.platform else 'Unknown'} for {self.source_target_type}:{self.source_target_id}>"
