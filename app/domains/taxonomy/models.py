from app.core.extensions import db
from app.domains.relationships import (
    content_topics,
    content_brands,
    content_attributes,
)
from app.shared.utils.slug import generate_slug, normalize_name


# ==================== METADATA MODELS ====================
class Source(db.Model):
    __tablename__ = "sources"
    id = db.Column(db.Integer, primary_key=True)
    external_uri = db.Column(db.String(255), unique=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    domain = db.Column(db.String(255), unique=True, nullable=False, index=True)
    logo_url = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    authority_score = db.Column(db.Integer, default=50, nullable=False)

    @staticmethod
    def get_by_slug(slug, session):
        return session.query(Source).filter_by(slug=slug).first()

    @staticmethod
    def get_by_domain(domain, session):
        return session.query(Source).filter_by(domain=domain).first()

    @staticmethod
    def get_or_create(name, domain, session):
        """Checks for source existence by domain, creates if missing."""
        if not domain or not name:
            return None
        source = Source.get_by_domain(domain, session)
        if not source:
            slug = generate_slug(name)
            source = Source(
                name=name,
                slug=slug,
                domain=domain
            )
            session.add(source)
            session.flush()
        return source

    article_sources = db.relationship("ArticleSource", back_populates="source")

    def __repr__(self):
        return f"<Source {self.name}>"


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

    contents = db.relationship("Content", back_populates="section")

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

    @staticmethod
    def get_or_create(name, session):
        """Checks for topic existence, creates if missing."""
        if not name:
            return None
        slug = generate_slug(name)
        topic = Topic.get_by_slug(slug, session)
        if not topic:
            topic = Topic(name=name, slug=slug, normalized_name=normalize_name(name))
            session.add(topic)
            session.flush()
        return topic

    contents = db.relationship(
        "Content", secondary=content_topics, back_populates="topics"
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

    @staticmethod
    def get_or_create(name, session, industry=None):
        """Checks for brand existence, creates if missing."""
        if not name:
            return None
        slug = generate_slug(name)
        brand = Brand.get_by_slug(slug, session)
        if not brand:
            brand = Brand(
                name=name,
                slug=slug,
                normalized_name=normalize_name(name),
                industry=industry,
            )
            session.add(brand)
            session.flush()  # Makes brand.id available for relationships
        return brand

    contents = db.relationship(
        "Content", secondary=content_brands, back_populates="brands"
    )
    items = db.relationship("Item", back_populates="brand")

    def __repr__(self):
        return f"<Brand {self.slug}>"


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    external_uri = db.Column(db.String(255), unique=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    normalized_name = db.Column(db.String(150), index=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    parent_id = db.Column(
        db.Integer, db.ForeignKey("categories.id", ondelete="CASCADE"), nullable=True
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
            is_leaf=is_leaf,
        )

    @staticmethod
    def get_by_slug(slug, session):
        return session.query(Category).filter_by(slug=slug).first()

    @staticmethod
    def get_or_create(name: str, session, parent=None, is_leaf=True):
        """Checks for category existence by slug, creates if missing."""
        if not name:
            return None
        slug = generate_slug(name)
        category = Category.get_by_slug(slug, session)
        if not category:
            category = Category.create(name=name, parent=parent, is_leaf=is_leaf)
            session.add(category)
            session.flush()
        return category

    parent = db.relationship("Category", remote_side=[id], backref="children")
    contents = db.relationship("Content", back_populates="category")
    items = db.relationship("Item", back_populates="category")

    def __repr__(self):
        return f"<Category {self.slug}>"


class GenderFacet(db.Model):
    __tablename__ = "gender_facets"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)

    @staticmethod
    def get_by_slug(slug, session):
        return session.query(GenderFacet).filter_by(slug=slug).first()

    contents = db.relationship("Content", back_populates="gender")


class IntentFacet(db.Model):
    __tablename__ = "intent_facets"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)

    @staticmethod
    def get_by_slug(slug, session):
        return session.query(IntentFacet).filter_by(slug=slug).first()

    @staticmethod
    def get_or_create(name, session):
        """Checks for Intent existence, creates if missing."""
        if not name:
            return None
        slug = generate_slug(name)
        intent = IntentFacet.get_by_slug(slug, session)
        if not intent:
            intent = IntentFacet(name=name, slug=slug)
            session.add(intent)
            session.flush()
        return intent

    contents = db.relationship("Content", back_populates="intent")


class PriceTierFacet(db.Model):
    __tablename__ = "price_tier_facets"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)

    @staticmethod
    def get_by_slug(slug, session):
        return session.query(PriceTierFacet).filter_by(slug=slug).first()

    @staticmethod
    def get_or_create(name, session):
        """Checks for Intent existence, creates if missing."""
        if not name:
            return None
        slug = generate_slug(name)
        price_tier = PriceTierFacet.get_by_slug(slug, session)
        if not price_tier:
            price_tier = PriceTierFacet(name=name, slug=slug)
            session.add(price_tier)
            session.flush()
        return price_tier

    contents = db.relationship("Content", back_populates="price_tier")


class AttributeFacet(db.Model):
    __tablename__ = "attributes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)

    @staticmethod
    def get_by_slug(slug, session):
        return session.query(AttributeFacet).filter_by(slug=slug).first()

    @staticmethod
    def get_or_create(name, session, category_id=None):
        """Checks for attribute existence, creates if missing."""
        if not name:
            return None
        slug = generate_slug(name)
        attr = AttributeFacet.get_by_slug(slug, session)
        if not attr:
            attr = AttributeFacet(name=name, slug=slug, category_id=category_id)
            session.add(attr)
            session.flush()
        return attr

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    category = db.relationship("Category")

    contents = db.relationship(
        "Content", secondary=content_attributes, back_populates="attributes"
    )



class Entity(db.Model):
    __tablename__ = "entities"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False) # Diffbot label / NewsAPI label
    slug = db.Column(db.String(150), unique=True, nullable=False, index=True)
    external_uri = db.Column(db.String(255), unique=True, index=True)
    entity_type = db.Column(db.String(50), index=True)
    image_url = db.Column(db.Text)

    @staticmethod
    def get_or_create(name, session, external_uri=None, entity_type=None):
        if not name:
            return None
        slug = generate_slug(name)
        
        entity = None
        if external_uri:
            entity = session.query(Entity).filter_by(external_uri=external_uri).first()
        if not entity:
            entity = session.query(Entity).filter_by(slug=slug).first()
            
        if not entity:
            entity = Entity(
                name=name,
                slug=slug,
                external_uri=external_uri,
                entity_type=entity_type
            )
            session.add(entity)
            session.flush()
        return entity

    content_entities = db.relationship("ContentEntity", back_populates="entity")

class Location(db.Model):
    __tablename__ = "locations"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(150), unique=True, nullable=False, index=True)
    country_code = db.Column(db.String(10), index=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    @staticmethod
    def get_or_create(name, session, country_code=None):
        if not name:
            return None
        slug = generate_slug(name)
        location = session.query(Location).filter_by(slug=slug).first()
        if not location:
            location = Location(
                name=name,
                slug=slug,
                country_code=country_code
            )
            session.add(location)
            session.flush()
        return location

    contents = db.relationship(
        "Content", secondary="content_locations", back_populates="locations"
    )
