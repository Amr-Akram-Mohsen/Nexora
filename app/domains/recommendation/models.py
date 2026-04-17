from datetime import datetime, timezone
from app.core.extensions import db

class UserInterest(db.Model):
    __tablename__ = "user_interests"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)  # 'item' or 'article'
    target_id = db.Column(db.Integer, nullable=False)
    interaction_count = db.Column(db.Integer, default=0)
    last_interaction_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = db.relationship("User", back_populates="user_interests")
    entity_scores = db.relationship("UserEntityInterest", back_populates="user_interest", cascade="all, delete-orphan")
    
    __table_args__ = (
        db.UniqueConstraint("user_id", "target_type", "target_id", name="uq_user_target"),
        db.Index("ix_user_interest_user_target", "user_id", "target_type", "target_id"),
        db.CheckConstraint("target_type IN ('item', 'article')", name="ck_target_type"),
    )

class UserEntityInterest(db.Model):
    __tablename__ = "user_entity_interests"
    id = db.Column(db.Integer, primary_key=True)
    user_interest_id = db.Column(db.Integer, db.ForeignKey("user_interests.id", ondelete="CASCADE"), nullable=False)
    brand_id = db.Column(db.Integer, nullable=True)
    category_id = db.Column(db.Integer, nullable=True)
    topic_id = db.Column(db.Integer, nullable=True)
    score = db.Column(db.Float, default=0.0)
    
    user_interest = db.relationship("UserInterest", back_populates="entity_scores")
    
    __table_args__ = (
        db.CheckConstraint("(brand_id IS NOT NULL) OR (category_id IS NOT NULL) OR (topic_id IS NOT NULL)", name="ck_entity_reference"),
        db.Index("ix_user_entity_interest_ref", "brand_id", "category_id", "topic_id"),
    )
