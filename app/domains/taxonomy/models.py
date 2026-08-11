from app.core.extensions import db
from app.shared.utils.slug import generate_slug, normalize_name
from app.domains.relationships import content_attributes
class Source(db.Model):
    __tablename__ = 'sources'
    id = db.Column(db.Integer, primary_key=True)
    external_uri = db.Column(db.String(255), unique=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    domain = db.Column(db.String(255), unique=True, nullable=False, index=True)
    logo_url = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    authority_score = db.Column(db.Integer, default=50, nullable=False)
    @staticmethod
    def get_by_slug(slug, session):
        return session.query(Source).filter_by(slug=slug).first()
    @staticmethod
    def get_by_domain(domain, session):
        return session.query(Source).filter_by(domain=domain).first()
    @staticmethod
    def get_or_create(name, domain, session):
        if not domain or not name:
            return None
        source = Source.get_by_domain(domain, session)
        if not source:
            slug = generate_slug(name)
            source = Source(name=name, slug=slug, domain=domain)
            session.add(source)
            session.flush()
        return source
    article_sources = db.relationship('ArticleSource', back_populates='source')
    def __repr__(self):
        return f'<Source {self.name}>'
class Section(db.Model):
    __tablename__ = 'sections'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    allowed_filters = db.Column(db.JSON, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    @staticmethod
    def get_by_slug(slug, session):
        return session.query(Section).filter_by(slug=slug).first()
    contents = db.relationship('Content', back_populates='section')
    def __repr__(self):
        return f"<Section id={self.id} name='{self.name}'>"
class Brand(db.Model):
    __tablename__ = 'brands'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    normalized_name = db.Column(db.String(150), index=True)
    slug = db.Column(db.String(150), unique=True, nullable=False, index=True)
    industry = db.Column(db.String(50), index=True)
    is_featured = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    @staticmethod
    def get_by_slug(slug, session):
        return session.query(Brand).filter_by(slug=slug).first()
    @staticmethod
    def get_or_create(name, session, industry=None):
        if not name:
            return None
        slug = generate_slug(name)
        brand = Brand.get_by_slug(slug, session)
        if not brand:
            brand = Brand(name=name, slug=slug, normalized_name=normalize_name(name), industry=industry)
            session.add(brand)
            session.flush()
        return brand
    products = db.relationship('Product', back_populates='brand')
    def __repr__(self):
        return f'<Brand {self.slug}>'
class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    external_uri = db.Column(db.String(255), unique=True, index=True)
    name = db.Column(db.String(255), nullable=False)
    normalized_name = db.Column(db.String(255), index=True)
    slug = db.Column(db.String(255), unique=True, nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='CASCADE'), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_leaf = db.Column(db.Boolean, default=True, nullable=False, index=True)
    @staticmethod
    def create(name: str, parent=None, is_leaf=True):
        return Category(name=name, slug=generate_slug(name), normalized_name=normalize_name(name), parent=parent, is_leaf=is_leaf)
    @staticmethod
    def get_by_slug(slug, session):
        return session.query(Category).filter_by(slug=slug).first()
    @staticmethod
    def get_or_create(name: str, session, parent=None, is_leaf=True):
        if not name:
            return None
        slug = generate_slug(name)
        category = Category.get_by_slug(slug, session)
        if not category:
            category = Category.create(name=name, parent=parent, is_leaf=is_leaf)
            session.add(category)
            session.flush()
        return category
    @staticmethod
    def get_or_create_from_path(path: str, session):
        if not path:
            return None
        parts = path.split('/')
        provider_prefixes = ('dmoz', 'iptc', 'news')
        if parts[0].lower() in provider_prefixes:
            parts = parts[1:]
        if not parts:
            return None
        parent_cat = None
        current_path_so_far = []
        for i, part_name in enumerate(parts):
            is_leaf = i == len(parts) - 1
            current_path_so_far.append(part_name)
            cat = Category.get_or_create(name=part_name, session=session, parent=parent_cat, is_leaf=is_leaf)
            if is_leaf and (not cat.external_uri):
                cat.external_uri = path
            parent_cat = cat
        return parent_cat
    parent = db.relationship('Category', remote_side=[id], backref='children')
    contents = db.relationship('Content', back_populates='category')
    products = db.relationship('Product', back_populates='category')
    article_associations = db.relationship('ArticleCategory', back_populates='category', cascade='all, delete-orphan')
    def __repr__(self):
        return f'<Category {self.slug}>'
class GenderFacet(db.Model):
    __tablename__ = 'gender_facets'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    @staticmethod
    def get_by_slug(slug, session):
        return session.query(GenderFacet).filter_by(slug=slug).first()
    contents = db.relationship('Content', back_populates='gender')
class IntentFacet(db.Model):
    __tablename__ = 'intent_facets'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    @staticmethod
    def get_by_slug(slug, session):
        return session.query(IntentFacet).filter_by(slug=slug).first()
    @staticmethod
    def get_or_create(name, session):
        if not name:
            return None
        slug = generate_slug(name)
        intent = IntentFacet.get_by_slug(slug, session)
        if not intent:
            intent = IntentFacet(name=name, slug=slug)
            session.add(intent)
            session.flush()
        return intent
    contents = db.relationship('Content', back_populates='intent')
class PriceTierFacet(db.Model):
    __tablename__ = 'price_tier_facets'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    @staticmethod
    def get_by_slug(slug, session):
        return session.query(PriceTierFacet).filter_by(slug=slug).first()
    @staticmethod
    def get_or_create(name, session):
        if not name:
            return None
        slug = generate_slug(name)
        price_tier = PriceTierFacet.get_by_slug(slug, session)
        if not price_tier:
            price_tier = PriceTierFacet(name=name, slug=slug)
            session.add(price_tier)
            session.flush()
        return price_tier
    contents = db.relationship('Content', back_populates='price_tier')
class AttributeFacet(db.Model):
    __tablename__ = 'attributes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    @staticmethod
    def get_by_slug(slug, session):
        return session.query(AttributeFacet).filter_by(slug=slug).first()
    @staticmethod
    def get_or_create(name, session, category_id=None):
        if not name:
            return None
        slug = generate_slug(name)
        attr = AttributeFacet.get_by_slug(slug, session)
        if not attr:
            attr = AttributeFacet(name=name, slug=slug, category_id=category_id)
            session.add(attr)
            session.flush()
        return attr
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    category = db.relationship('Category')
    contents = db.relationship('Content', secondary=content_attributes, back_populates='attributes')
class Entity(db.Model):
    __tablename__ = 'entities'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False, index=True)
    external_uri = db.Column(db.String(255), unique=True, index=True)
    entity_type = db.Column(db.String(50), index=True)
    image_url = db.Column(db.Text)
    provider = db.Column(db.String(30), nullable=True, index=True)
    description = db.Column(db.Text, nullable=True)
    aliases = db.Column(db.JSON, nullable=True)
    wikidata_id = db.Column(db.String(50), nullable=True, index=True)
    wikipedia_url = db.Column(db.Text, nullable=True)
    content_entities = db.relationship('ContentEntity', back_populates='entity')
    @staticmethod
    def get_or_create(name, session, external_uri=None, entity_type=None, provider=None, image_url=None):
        if not name:
            return None
        slug = generate_slug(name)
        entity = None
        if external_uri:
            entity = session.query(Entity).filter_by(external_uri=external_uri).first()
        if not entity:
            entity = session.query(Entity).filter_by(slug=slug).first()
        if not entity:
            entity = session.query(Entity).filter_by(slug=slug).first()
        if not entity:
            entity = Entity(name=name, slug=slug, external_uri=external_uri, entity_type=entity_type, provider=provider, image_url=image_url, aliases=[])
            session.add(entity)
            session.flush()
        else:
            if entity_type and (not entity.entity_type):
                entity.entity_type = entity_type
            if external_uri and (not entity.external_uri):
                entity.external_uri = external_uri
            if provider and (not entity.provider):
                entity.provider = provider
            if image_url and (not entity.image_url):
                entity.image_url = image_url
        return entity
    @staticmethod
    def get_by_slug(slug, session):
        return session.query(Entity).filter_by(slug=slug).first()
    @staticmethod
    def get_by_uri(external_uri, session):
        if not external_uri:
            return None
        return session.query(Entity).filter_by(external_uri=external_uri).first()
class Location(db.Model):
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(150), unique=True, nullable=False, index=True)
    country_code = db.Column(db.String(10), index=True)
    country_name = db.Column(db.String(150))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    @staticmethod
    def get_or_create(name, session, country_code=None, country_name=None):
        if not name:
            return None
        slug = generate_slug(name)
        location = session.query(Location).filter_by(slug=slug).first()
        if not location:
            location = Location(name=name, slug=slug, country_code=country_code, country_name=country_name)
            session.add(location)
            session.flush()
        else:
            if country_name and (not location.country_name):
                location.country_name = country_name
            if country_code and (not location.country_code):
                location.country_code = country_code
        return location
    contents = db.relationship('Content', secondary='content_locations', back_populates='locations')