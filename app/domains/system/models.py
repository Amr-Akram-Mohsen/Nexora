from app.core.extensions import db
from app.domains.article.relationships import (article_sections, article_topics, article_brands, item_sections, item_topics, article_attributes)
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
    
    @staticmethod
    def get_by_slug(slug, session):
        return session.query(Section).filter_by(slug=slug).first()

    articles = db.relationship(
        "Article",
        back_populates="section"
    )
    items = db.relationship(
        "Item",
        back_populates="section"
    )

    def __repr__(self):
        return f"<Section id={self.id} name='{self.name}'>"

class Topic(db.Model):
    __tablename__ = "topics"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    normalized_name = db.Column(db.String(150), index=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    is_featured = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)

    @staticmethod
    def get_by_slug(slug, session):
        return session.query(Topic).filter_by(slug=slug).first()
        
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
    def get_by_slug(slug, session):
        return session.query(Brand).filter_by(slug=slug).first()
    
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
    is_leaf = db.Column(db.Boolean, default=True, index=True)

    @staticmethod
    def create(name: str, parent=None, is_leaf=True):
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



class GenderFacet(db.Model):
    __tablename__ = "gender_facets"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)

    articles = db.relationship("Article", back_populates="gender")

class IntentFacet(db.Model):
    __tablename__ = "intent_facets"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)

    articles = db.relationship("Article", back_populates="intent")

class PriceTierFacet(db.Model):
    __tablename__ = "price_tier_facets"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)

    articles = db.relationship("Article", back_populates="price_tier")

class AttributeFacet(db.Model):
    __tablename__ = "attributes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)


    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    category = db.relationship("Category")
    
    articles = db.relationship(
        "Article",
        secondary=article_attributes,
        back_populates="attributes"
    )
