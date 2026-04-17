from datetime import datetime, timezone
from app.core.extensions import db

class Reaction(db.Model):
    __tablename__ = "reactions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)  # 'article' or 'item' or 'comment'
    target_id = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(20), nullable=False)         # 'like', 'dislike', etc.
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    @property
    def target(self):
        return self.article or self.item or self.comment
    
    user = db.relationship("User", back_populates="reactions")
    
    article = db.relationship(
        "Article",
        primaryjoin="and_(foreign(Reaction.target_id) == Article.id, Reaction.target_type == 'article')",
        back_populates="reactions",
        viewonly=True,
        lazy="selectin"
    )
    item = db.relationship(
        "Item",
        primaryjoin="and_(foreign(Reaction.target_id) == Item.id, Reaction.target_type == 'item')",
        back_populates="reactions",
        viewonly=True,
        lazy="selectin"
    )
    comment = db.relationship(
        "Comment",
        primaryjoin="and_(foreign(Reaction.target_id) == Comment.id, Reaction.target_type == 'comment')",
        back_populates="reactions",
        viewonly=True,
        lazy="selectin"
    )

    __table_args__ = (
        db.Index("idx_reactions_target", "target_type", "target_id"),
        db.UniqueConstraint('user_id', 'target_type', 'target_id', name='unique_user_reaction'),
        db.CheckConstraint(
            "target_type IN ('article', 'item', 'comment')",
            name="ck_reaction_target_type"
        ),
    )

    def __repr__(self):
        return (
            f"<Reaction id={self.id} "
            f"user={self.user_id} "
            f"{self.type} "
            f"{self.target_type}:{self.target_id}>"
        )

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)  # 'article' or 'item'
    target_id = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    parent_id = db.Column(db.Integer, db.ForeignKey("comments.id", ondelete="CASCADE"), nullable=True)
    sentiment = db.Column(db.String(20), nullable=True)
    confidence = db.Column(db.Float, nullable=True)
    likes_count = db.Column(db.Integer, default=0)
    dislikes_count = db.Column(db.Integer, default=0)

    @property
    def target(self):
        return self.article or self.item

    user = db.relationship("User", back_populates="comments")
    parent = db.relationship("Comment", remote_side=[id], back_populates="replies")
    replies = db.relationship("Comment", back_populates="parent", cascade="all, delete-orphan")
    
    article = db.relationship(
        "Article",
        primaryjoin="and_(foreign(Comment.target_id) == Article.id, Comment.target_type == 'article')",
        back_populates="comments",
        viewonly=True,
        lazy="selectin"
    )
    item = db.relationship(
        "Item",
        primaryjoin="and_(foreign(Comment.target_id) == Item.id, Comment.target_type == 'item')",
        back_populates="comments",
        viewonly=True,
        lazy="selectin"
    )
    reactions = db.relationship(
        "Reaction",
        primaryjoin="and_(foreign(Reaction.target_id) == Comment.id, Reaction.target_type == 'comment')",
        back_populates="comment",
        viewonly=True,
        lazy="selectin"
    )

    __table_args__ = (
        db.Index("idx_comments_target", "target_type", "target_id"),
        db.CheckConstraint("target_type IN ('article', 'item')", name="ck_comment_target_type"),
    )

    def __repr__(self):
        return (
            f"<Comment id={self.id} "
            f"user={self.user_id} "
            f"{self.target_type}:{self.target_id} "
            f"parent={self.parent_id}>"
        )

class View(db.Model):
    __tablename__ = "views"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    target_type = db.Column(db.String(50), nullable=False)  # 'article' or 'item'
    target_id = db.Column(db.Integer, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def target(self):
        return self.article or self.item

    user = db.relationship("User", back_populates="views")
    article = db.relationship(
        "Article",
        primaryjoin="and_(foreign(View.target_id) == Article.id, View.target_type == 'article')",
        back_populates="views",
        viewonly=True,
        lazy="selectin"
    )
    item = db.relationship(
        "Item",
        primaryjoin="and_(foreign(View.target_id) == Item.id, View.target_type == 'item')",
        back_populates="views",
        viewonly=True,
        lazy="selectin"
    )

    __table_args__ = (
        db.Index("idx_views_target", "target_type", "target_id"),
        db.CheckConstraint("(user_id IS NOT NULL AND ip_address IS NULL) OR (user_id IS NULL AND ip_address IS NOT NULL)", name="ck_view_one_identity"),
        db.UniqueConstraint("user_id", "ip_address", "target_type", "target_id", name="unique_view"),
        db.CheckConstraint("target_type IN ('article', 'item')", name="ck_view_target_type"),
    )

    def __repr__(self):
        viewer = f"user={self.user_id}" if self.user_id else f"ip={self.ip_address}"
        return f"<View {viewer} {self.target_type}:{self.target_id}>"

class Save(db.Model):
    __tablename__ = "saves"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    article = db.relationship(
        "Article",
        primaryjoin="and_(foreign(Save.target_id) == Article.id, Save.target_type == 'article')",
        viewonly=True,
        lazy="selectin"
    )
    item = db.relationship(
        "Item",
        primaryjoin="and_(foreign(Save.target_id) == Item.id, Save.target_type == 'item')",
        viewonly=True,
        lazy="selectin"
    )

    @property
    def target(self):
        return self.article or self.item

    user = db.relationship("User", back_populates="saves")

    __table_args__ = (
        db.UniqueConstraint("user_id", "target_type", "target_id", name="uq_user_save"),
        db.Index("ix_save_target", "target_type", "target_id"),
        db.CheckConstraint("target_type IN ('article', 'item')", name="ck_save_target_type"),
    )

    def __repr__(self):
        return f"<Save user={self.user_id} {self.target_type}:{self.target_id}>"

class ItemClick(db.Model):
    __tablename__ = "item_clicks"
    id = db.Column(db.Integer, primary_key=True)
    item_store_link_id = db.Column(db.Integer, db.ForeignKey("item_store_links.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    referrer = db.Column(db.Text)
    country = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, server_default=db.func.now(), index=True)

    user = db.relationship("User", back_populates="item_clicks")
    item_store_link = db.relationship("ItemStoreLink")

    __table_args__ = (
        db.Index("ix_item_click_link", "item_store_link_id"),
        db.Index("ix_item_click_user", "user_id"),
    )

    def __repr__(self):
        return f"<ItemClick id={self.id} link={self.item_store_link_id} user={self.user_id} ip={self.ip_address}>"
