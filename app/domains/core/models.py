from app.core.extensions import db
from .relationships import (article_sections, article_topics, article_brands, item_sections, item_topics)
from app.shared.utils.slug import generate_slug, normalize_name
# ==================== METADATA MODELS ====================
class Section(db.Model):
    __tablename__ = "sections"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    allowed_filters = db.Column(db.JSON, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    
    articles = db.relationship(
        "Article",
        secondary=article_sections,
        back_populates="sections"
    )
    items = db.relationship(
        "Item",
        secondary=item_sections,
        back_populates="sections"
    )

    def __repr__(self):
        return f"<Section id={self.id} name='{self.name}'>"

class Topic(db.Model):
    __tablename__ = "topics"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    normalized_name = db.Column(db.String(150), index=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    type = db.Column(db.String(50), nullable=True)
    is_featured = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)

    @staticmethod
    def get_or_create(name: str, session):
        normalized = normalize_name(name)

        obj = session.query(Topic).filter_by(normalized_name=normalized).first()
        if obj:
            return obj

        obj = Topic(
            name=name,
            slug=generate_slug(name),
            normalized_name=normalized
        )
        session.add(obj)
        return obj
    
    
    articles = db.relationship(
        "Article",
        secondary=article_topics,
        back_populates="topics"
    )
    items = db.relationship(
        "Item",
        secondary=item_topics,
        back_populates="topics"
    )

    def __repr__(self):
        return f"<Topic {self.slug}>"

class Brand(db.Model):
    __tablename__ = "brands"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    normalized_name = db.Column(db.String(150), index=True)
    slug = db.Column(db.String(150), unique=True, nullable=False, index=True)
    industry = db.Column(db.String(50), index=True)
    is_featured = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)

    @staticmethod
    def get_or_create(name: str, session, industry: str = None):
        normalized = normalize_name(name)

        obj = session.query(Brand).filter_by(normalized_name=normalized).first()
        if obj:
            return obj

        obj = Brand(
            name=name,
            slug=generate_slug(name),
            normalized_name=normalized,
            industry=industry or "general"
        )
        session.add(obj)
        return obj
    
    
    articles = db.relationship(
        "Article",
        secondary=article_brands,
        back_populates="brands"
    )
    items = db.relationship(
        "Item",
        back_populates="brand"
    )

    def __repr__(self):
        return f"<Brand {self.slug}>"

class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    normalized_name = db.Column(db.String(150), index=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True
    )
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    is_leaf = db.Column(db.Boolean, default=False, index=True)

    @staticmethod
    def create(name: str, parent=None, is_leaf=False):
        return Category(
            name=name,
            slug=generate_slug(name),
            normalized_name=normalize_name(name),
            parent=parent,
            is_leaf=is_leaf
        )

    @staticmethod
    def get_by_slug(slug, session):
        return session.query(Category).filter_by(slug=slug).first()
    
    parent = db.relationship(
        "Category",
        remote_side=[id],
        backref="children"
    )
    articles = db.relationship(
        "Article",
        back_populates="category"
    )
    items = db.relationship(
        "Item",
        back_populates="category"
    )
    
    def __repr__(self):
        return f"<Category {self.slug}>"
