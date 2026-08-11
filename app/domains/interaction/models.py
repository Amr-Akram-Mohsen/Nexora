from datetime import datetime, timezone
from app.core.extensions import db
class Reaction(db.Model):
    __tablename__ = 'reactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    @property
    def target(self):
        return self.content or self.product or self.comment
    user = db.relationship('User', back_populates='reactions')
    content = db.relationship('Content', primaryjoin="and_(foreign(Reaction.target_id) == Content.id, Reaction.target_type == 'content')", back_populates='reactions', viewonly=True, lazy='selectin')
    product = db.relationship('Product', primaryjoin="and_(foreign(Reaction.target_id) == Product.id, Reaction.target_type == 'product')", back_populates='reactions', viewonly=True, lazy='selectin')
    comment = db.relationship('Comment', primaryjoin="and_(foreign(Reaction.target_id) == Comment.id, Reaction.target_type == 'comment')", back_populates='reactions', viewonly=True, lazy='selectin')
    __table_args__ = (db.Index('ix_reactions_target', 'target_type', 'target_id'), db.UniqueConstraint('user_id', 'target_type', 'target_id', name='unique_user_reaction'), db.CheckConstraint("target_type IN ('content', 'product', 'comment')", name='ck_reaction_target_type'))
    def __repr__(self):
        return f'<Reaction id={self.id} user={self.user_id} {self.type} {self.target_type}:{self.target_id}>'
class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False, default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id', ondelete='CASCADE'), nullable=True)
    sentiment = db.Column(db.String(20), nullable=True)
    confidence = db.Column(db.Float, nullable=True)
    like_count = db.Column(db.Integer, nullable=False, default=0)
    dislike_count = db.Column(db.Integer, nullable=False, default=0)
    share_count = db.Column(db.Integer, nullable=False, default=0)
    replies_count = db.Column(db.Integer, nullable=False, default=0)
    @property
    def target(self):
        return self.content_target or self.product
    user = db.relationship('User', back_populates='comments')
    parent = db.relationship('Comment', remote_side=[id], back_populates='replies')
    replies = db.relationship('Comment', back_populates='parent', cascade='all, delete-orphan')
    content_target = db.relationship('Content', primaryjoin="and_(foreign(Comment.target_id) == Content.id, Comment.target_type == 'content')", back_populates='comments', viewonly=True, lazy='selectin')
    product = db.relationship('Product', primaryjoin="and_(foreign(Comment.target_id) == Product.id, Comment.target_type == 'product')", back_populates='comments', viewonly=True, lazy='selectin')
    reactions = db.relationship('Reaction', primaryjoin="and_(foreign(Reaction.target_id) == Comment.id, Reaction.target_type == 'comment')", back_populates='comment', viewonly=True, lazy='selectin')
    __table_args__ = (db.Index('ix_comments_target', 'target_type', 'target_id'), db.CheckConstraint("target_type IN ('content', 'product')", name='ck_comment_target_type'))
    def __repr__(self):
        return f'<Comment id={self.id} user={self.user_id} {self.target_type}:{self.target_id} parent={self.parent_id}>'
class View(db.Model):
    __tablename__ = 'views'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    target_type = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    @property
    def target(self):
        return self.content or self.product
    user = db.relationship('User', back_populates='views')
    content = db.relationship('Content', primaryjoin="and_(foreign(View.target_id) == Content.id, View.target_type == 'content')", back_populates='views', viewonly=True, lazy='selectin')
    product = db.relationship('Product', primaryjoin="and_(foreign(View.target_id) == Product.id, View.target_type == 'product')", back_populates='views', viewonly=True, lazy='selectin')
    __table_args__ = (db.Index('ix_views_target', 'target_type', 'target_id'), db.CheckConstraint('(user_id IS NOT NULL AND ip_address IS NULL) OR (user_id IS NULL AND ip_address IS NOT NULL)', name='ck_view_one_identity'), db.UniqueConstraint('user_id', 'ip_address', 'target_type', 'target_id', name='unique_view'), db.CheckConstraint("target_type IN ('content', 'product')", name='ck_view_target_type'))
    def __repr__(self):
        viewer = f'user={self.user_id}' if self.user_id else f'ip={self.ip_address}'
        return f'<View {viewer} {self.target_type}:{self.target_id}>'
class Save(db.Model):
    __tablename__ = 'saves'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    collection_name = db.Column(db.String(100), nullable=True, default='General')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    content = db.relationship('Content', primaryjoin="and_(foreign(Save.target_id) == Content.id, Save.target_type == 'content')", viewonly=True, lazy='selectin')
    product = db.relationship('Product', primaryjoin="and_(foreign(Save.target_id) == Product.id, Save.target_type == 'product')", viewonly=True, lazy='selectin')
    @property
    def target(self):
        return self.content or self.product
    user = db.relationship('User', back_populates='saves')
    __table_args__ = (db.UniqueConstraint('user_id', 'target_type', 'target_id', 'collection_name', name='uq_user_save_collection'), db.Index('ix_save_target', 'target_type', 'target_id'), db.CheckConstraint("target_type IN ('content', 'product')", name='ck_save_target_type'))
    def __repr__(self):
        return f'<Save user={self.user_id} {self.target_type}:{self.target_id}>'
class Share(db.Model):
    __tablename__ = 'shares'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    channel = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user = db.relationship('User', back_populates='shares')
    content = db.relationship('Content', primaryjoin="and_(foreign(Share.target_id) == Content.id, Share.target_type == 'content')", viewonly=True, lazy='selectin')
    product = db.relationship('Product', primaryjoin="and_(foreign(Share.target_id) == Product.id, Share.target_type == 'product')", viewonly=True, lazy='selectin')
    @property
    def target(self):
        return self.content or self.product
    __table_args__ = (db.Index('ix_share_target', 'target_type', 'target_id'), db.Index('ix_share_user_created', 'user_id', 'created_at'), db.CheckConstraint("target_type IN ('content', 'product')", name='ck_share_target_type'))
    def __repr__(self):
        return f'<Share user={self.user_id} {self.target_type}:{self.target_id}>'
class ProductClick(db.Model):
    __tablename__ = 'product_clicks'
    id = db.Column(db.Integer, primary_key=True)
    product_store_link_id = db.Column(db.Integer, db.ForeignKey('product_store_links.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    referrer = db.Column(db.Text)
    country = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, server_default=db.func.now(), index=True)
    user = db.relationship('User', back_populates='product_clicks')
    product_store_link = db.relationship('ProductStoreLink')
    __table_args__ = (db.Index('ix_product_click_link', 'product_store_link_id'), db.Index('ix_product_click_user', 'user_id'))
    def __repr__(self):
        return f'<ProductClick id={self.id} link={self.product_store_link_id} user={self.user_id} ip={self.ip_address}>'
class RecommendationImpression(db.Model):
    __tablename__ = 'recommendation_impressions'
    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(50), nullable=False)
    context_id = db.Column(db.String(100), nullable=True)
    entity_ids = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), server_default=db.func.now(), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    def __repr__(self):
        return f'<RecommendationImpression id={self.id} type={self.entity_type} context={self.context_id}>'
class RecommendationClick(db.Model):
    __tablename__ = 'recommendation_clicks'
    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.String(100), nullable=False)
    context_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), server_default=db.func.now(), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    def __repr__(self):
        return f'<RecommendationClick id={self.id} type={self.entity_type} target={self.entity_id} context={self.context_id}>'