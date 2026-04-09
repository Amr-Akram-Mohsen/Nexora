from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
db = SQLAlchemy()
import secrets
from functools import cached_property
from app.utils.sanitizer import sanitize_json

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    google_id = db.Column(db.String(120), unique=True, nullable=True)
    provider = db.Column(db.String(50), nullable=True)  # 'google' or 'local'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    
    
    # Relationships
    newsletter_subscription = db.relationship(
        "NewsletterSubscriber",
        back_populates="user",
        uselist=False
    )
    # inside User class
    reactions = db.relationship("Reaction", back_populates="user", cascade="all, delete-orphan")
    comments = db.relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    views = db.relationship("View", back_populates="user", cascade="all, delete-orphan")
    saves = db.relationship(
        "Save",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    user_interests = db.relationship(
        "UserInterest",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    item_clicks = db.relationship("ItemClick", back_populates="user")
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    __table_args__ = (
        db.CheckConstraint(
            "(google_id IS NULL AND provider IS NULL) OR (google_id IS NOT NULL AND provider IS NOT NULL)",
            name="ck_google_user"
        ),
    )
    def __repr__(self):
        return f'<User {self.email}>'
class NewsletterSubscriber(db.Model):
    __tablename__ = 'newsletter_subscribers'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    is_confirmed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    unsubscribed_at = db.Column(db.DateTime, nullable=True)
    confirmation_token = db.Column(db.String(255), nullable=True)
    unsubscribe_token = db.Column(db.String(255), nullable=True)    
    user = db.relationship("User", back_populates="newsletter_subscription")

    # 🔥 Helpers
    def generate_tokens(self):
        self.confirmation_token = secrets.token_urlsafe(32)
        self.unsubscribe_token = secrets.token_urlsafe(32)

    @property
    def is_active(self):
        return self.is_confirmed and self.unsubscribed_at is None
        
    def __repr__(self):
        return f'<NewsletterSubscriber {self.email}>'
# ==================== ASSOCIATION TABLES ====================
article_sections = db.Table(
    "article_sections",
    db.Column("article_id", db.Integer, db.ForeignKey(
        "articles.id"), primary_key=True),
    db.Column("section_id", db.Integer, db.ForeignKey(
        "sections.id"), primary_key=True)
)
item_sections = db.Table(
    "item_sections",
    db.Column("item_id", db.Integer, db.ForeignKey(
        "items.id"), primary_key=True),
    db.Column("section_id", db.Integer, db.ForeignKey(
        "sections.id"), primary_key=True)
)
article_topics = db.Table(
    "article_topics",
    db.Column("article_id", db.Integer, db.ForeignKey("articles.id"), primary_key=True),
    db.Column("topic_id", db.Integer, db.ForeignKey("topics.id"), primary_key=True)
)
article_brands = db.Table(
    "article_brands",
    db.Column("article_id", db.Integer, db.ForeignKey(
        "articles.id"), primary_key=True),
    db.Column("brand_id", db.Integer, db.ForeignKey(
        "brands.id"), primary_key=True)
)
item_topics = db.Table(
    "item_topics",
    db.Column("item_id", db.Integer, db.ForeignKey("items.id"), primary_key=True),
    db.Column("topic_id", db.Integer, db.ForeignKey("topics.id"), primary_key=True)
)
# Links a review/article directly to the product(s) it covers
article_items = db.Table(
    "article_items",
    db.Column("article_id", db.Integer, db.ForeignKey("articles.id"), primary_key=True),
    db.Column("item_id",    db.Integer, db.ForeignKey("items.id"),    primary_key=True)
)
# ==================== SECTION ====================
class Section(db.Model):
    __tablename__ = "sections"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
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
    slug = db.Column(db.String(120), unique=True, nullable=False)
    type = db.Column(db.String(50), nullable=True)
    is_featured = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
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
    slug = db.Column(db.String(150), unique=True, nullable=False)
    is_featured = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
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
    slug = db.Column(db.String(120), unique=True, nullable=False)
    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True
    )
    parent = db.relationship(
        "Category",
        remote_side=[id],
        backref="children"
    )
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
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
# ==================== ARTICLE ====================
class Article(db.Model):
    __tablename__ = "articles"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text)
    url = db.Column(db.Text, nullable=False, unique=True)
    source_id = db.Column(db.String(120))
    source_name = db.Column(db.String(200))
    published_at = db.Column(db.DateTime)
    retrieved_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    image_url = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    comment_count = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)
    card_type = db.Column(db.TEXT, default="article")
    # Tracker for matcher — set to utcnow() after each matching run
    last_matched_at = db.Column(db.DateTime, nullable=True, index=True)


    topics = db.relationship(
        "Topic", secondary=article_topics, back_populates="articles")
    sections = db.relationship(
        "Section", secondary=article_sections, back_populates="articles")
    brands = db.relationship(
        "Brand", secondary=article_brands, back_populates="articles")
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    category = db.relationship("Category", back_populates="articles")
    # Products this article reviews / mentions (admin-managed or matched by a future job)
    linked_items = db.relationship(
        "Item",
        secondary=article_items,
        back_populates="linked_articles"
    )
    # Reactions made on this article
    reactions = db.relationship(
        "Reaction",
        primaryjoin="and_(foreign(Reaction.target_id)==Article.id, Reaction.target_type=='article')",
        back_populates="article",
        viewonly=True,
        lazy="selectin"
    )
    # Comments on this article
    comments = db.relationship(
        "Comment",
        primaryjoin="and_(foreign(Comment.target_id)==Article.id, Comment.target_type=='article')",
        back_populates="article",
        viewonly=True,
        lazy="selectin"
    )
    # Views on this article
    views = db.relationship(
        "View",
        primaryjoin="and_(foreign(View.target_id)==Article.id, View.target_type=='article')",
        back_populates="article",
        viewonly=True,
        lazy="selectin"
    )
    __table_args__ = (
        db.Index("idx_published_at", "published_at"),
        db.UniqueConstraint('source_name', 'title', name='uq_articles_source_title'),
    )
    @property
    def read_time_minutes(self):
        text = (self.content or self.description or "")
        words = len(text.split())
        return max(1, words // 200)

    def __repr__(self):
        return f"<Article {self.title[:60]}>"
    # ---------------- Convenience helpers ----------------
    def add_section(self, section_obj):
        """Append Section object if not already present."""
        if section_obj not in self.sections:
            self.sections.append(section_obj)
    def add_brand(self, brand_obj):
        if brand_obj not in self.brands:
            self.brands.append(brand_obj)
    def add_topic(self, topic_obj):
        if topic_obj not in self.topics:
            self.topics.append(topic_obj)
    def link_item(self, item_obj):
        """Link this article to a product it reviews/mentions."""
        if item_obj not in self.linked_items:
            self.linked_items.append(item_obj)

class Store(db.Model):
    __tablename__ = "stores"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    website = db.Column(db.Text, nullable=False)
    country = db.Column(db.String(50))
    currency = db.Column(db.String(10))
    affiliate_network = db.Column(db.String(100))
    logo_url = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    item_links = db.relationship(
        "ItemStoreLink",
        back_populates="store",
        cascade="all, delete-orphan"
    )


class Item(db.Model):
    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), nullable=False, unique=True)
    description = db.Column(db.Text)  # optional short description
    rating = db.Column(db.Float)
    review_count = db.Column(db.Integer)  # optional short description
    
    # 🔥 NEW
    item_type = db.Column(db.String(50), nullable=True)  
    # examples: electronics, perfume
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=False)
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        index=True
    )
    comment_count = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)
    click_count = db.Column(db.Integer, default=0)
    card_type = db.Column(db.TEXT, default="item")
    searchable_attributes = db.Column(db.JSON) # Hoisted data for filtering
    
    # ── RELATIONSHIPS ──────────────────────────────────────────────
    category = db.relationship("Category", back_populates="items")
    brand = db.relationship("Brand", back_populates="items")
    sections = db.relationship(
        "Section", secondary=item_sections, back_populates="items")
    topics = db.relationship("Topic", secondary=item_topics, back_populates="items")
    # Articles that review or mention this product
    linked_articles = db.relationship(
        "Article",
        secondary=article_items,
        back_populates="linked_items"
    )
    # Relationships
    variants = db.relationship(
        "ItemVariant",
        back_populates="item",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    images = db.relationship(
        "ItemImage",
        back_populates="item",
        cascade="all, delete-orphan",
        order_by="ItemImage.position",
        lazy="selectin",
        overlaps="images" # Avoid collision if variant relationship uses back_populates="images"
    )    
    specifications = db.relationship(
        "ItemSpecification",
        back_populates="item",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def set_default_variant(self):
        if not self.variants:
            return

        if not any(v.is_default for v in self.variants):
            self.variants[0].is_default = True
    
    @property
    def image_url(self):
        return self.images[0].image_url if self.images else None

    @property
    def default_variant(self):
        return next(
            (v for v in self.variants if v.is_default),
            self.variants[0] if self.variants else None
        )

    @property
    def price(self):
        return self.default_variant.price if self.default_variant else None
    @property
    def min_price(self):
        return min(v.price for v in self.variants) if self.variants else None
    
    @property
    def has_variants(self):
        return len(self.variants) > 1

    @property
    def store_links(self):
        if not self.default_variant:
            return []

        return [
            link
            for link in self.default_variant.store_links
            if link.is_active
        ]

    @staticmethod
    def pick_keys(d, keys):
        if not isinstance(d, dict):
            return None
        result = {k: d[k] for k in keys if k in d and d[k] is not None}
        return result or None
    
    @staticmethod
    def get_specifications(result):
        return {k: v for k, v in result.items() if v}    
    
    @property
    def full_details(self):
        """
        Consolidates and sanitizes all specification fragments.
        """
        return {
            spec.category: sanitize_json(spec.spec_json)
            for spec in self.specifications
            if isinstance(spec.spec_json, dict)
        }

    @cached_property
    def structured_details(self):
        """
        Normalized structure for frontend based on item_type.
        No hardcoding of values, only structure mapping.
        """
        data = self.full_details

        if self.item_type == "electronics":
            return {
                "highlights": self.pick_keys(
                    {
                        **data.get("display", {}),
                        **data.get("platform", {}),
                        **data.get("battery", {}),
                    },
                    ["size", "chipset", "type"]
                ),
                "quick_details": data,
                "groups": data
            }

        elif self.item_type == "perfumes":
            fp = data.get("fragrance_profile", {})

            return {
                "scent": {
                    "top": fp.get("top_notes"),
                    "heart": fp.get("heart_notes"),
                    "base": fp.get("base_notes"),
                },
                "meta": self.pick_keys(
                    fp,
                    ["concentration", "scent_family"]
                ),
                "performance": data.get("performance", {}),
                "quick_details": data.get("performance", {}),
                "groups": data
            }

        elif self.item_type == "accessories":
            return {
                "materials": data.get("material_build", {}),
                "dimensions": data.get("dimensions", {}),
                "movement": data.get("movement", {}),
                "quick_details": data.get("movement", {}),
                "groups": data
            }

        return {
            "quick_details": data,
            "groups": data
        }

    def get_product_schema(self, request_url):
        """
        Generates Google-friendly JSON-LD Schema.
        """
        schema = {
            "@context": "https://schema.org/",
            "@type": "Product",
            "name": self.name,
            "description": self.description,
            "brand": {"@type": "Brand", "name": self.brand.name},
            "category": self.category.name,
            "url": request_url,
            "sku": self.default_variant.sku if self.default_variant else None
        }
        
        # Add images
        if self.images:
            schema["image"] = [img.image_url for img in self.images]
            
        # Add pricing from store links if available
        if self.store_links:
            offers = []
            for link in self.store_links:
                offers.append({
                    "@type": "Offer",
                    "price": float(link.price),
                    "priceCurrency": link.currency,
                    "availability": f"https://schema.org/{link.availability or 'InStock'}",
                    "url": link.affiliate_url
                })
            schema["offers"] = offers
            
        return schema

    @property
    def quick_details(self):
        return self._quick_details(self.structured_details.get("quick_details", {}))

    def _quick_details(self, details=None, parent=""):
        items = []
        for key, value in details.items():
            label = key.replace("_", " ").title()
            # if parent:
            #     label = f"{parent} {label}"
            current_group = parent or label

            if isinstance(value, dict):
                items.extend(self._quick_details(value, current_group))
            else:
                items.append({
                    "group": parent,
                    "label": label,
                    "value": value
                })
        return items
    
    
    # Reactions made on this item
    reactions = db.relationship(
        "Reaction",
        primaryjoin="and_(foreign(Reaction.target_id)==Item.id, Reaction.target_type=='item')",
        back_populates="item",
        viewonly=True,
        lazy="selectin"
    )
    # Comments on this item
    comments = db.relationship(
        "Comment",
        primaryjoin="and_(foreign(Comment.target_id)==Item.id, Comment.target_type=='item')",
        back_populates="item",
        viewonly=True,
        lazy="selectin"
    )
    # Views on this item
    views = db.relationship(
        "View",
        primaryjoin="and_(foreign(View.target_id)==Item.id, View.target_type=='item')",
        back_populates="item",
        viewonly=True,
        lazy="selectin"
    )
    __table_args__ = (
        db.Index("ix_items_slug", "slug"),  # optional, speeds up queries
    )    
    @property
    def rating(self):
        return 4.7

    @property
    def review_count(self):
        return 982

    def __repr__(self):
        return f"<Item {self.name}>"
    
    # ---------------- Convenience helpers ----------------
    def add_section(self, section_obj):
        """Append Section object if not already present."""
        if section_obj not in self.sections:
            self.sections.append(section_obj)
    def add_topic(self, topic_obj):
        if topic_obj not in self.topics:
            self.topics.append(topic_obj)
    def link_article(self, article_obj):
        """Link a review article to this product."""
        if article_obj not in self.linked_articles:
            self.linked_articles.append(article_obj)


class ItemVariant(db.Model):
    __tablename__ = "item_variants"
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(
        db.Integer,
        db.ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False
    )
    title = db.Column(db.String(200), nullable=True)
    sku = db.Column(db.String(100), unique=True, nullable=True)
    attributes = db.Column(db.JSON)  
    # example:
    # { "size": "100ml", "color": "Black" }
    is_default = db.Column(db.Boolean, default=False)
    
    # ── PRICING (Starting/Best Price) ──────────────────────────
    price = db.Column(db.Numeric(10, 2))
    old_price = db.Column(db.Numeric(10, 2))
    currency = db.Column(db.String(3)) # e.g. SAR, AED
    
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    # relationships
    item = db.relationship("Item", back_populates="variants")    
    images = db.relationship("ItemImage", back_populates="variant", cascade="all, delete-orphan")
    store_links = db.relationship(
        "ItemStoreLink",
        back_populates="variant",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def normalize_attributes(self):
        if not self.attributes:
            return

        self.attributes = {
            str(k).lower().strip(): str(v).strip()
            for k, v in self.attributes.items()
        }

    def display_name(self):
        if self.title:
            return self.title
        if self.attributes:
            return " / ".join(
                f"{k.capitalize()}: {v}"
                for k, v in self.attributes.items()
            )
        return "Default"
    
    __table_args__ = (
        db.Index("ix_variant_item", "item_id"),
        db.Index("ix_variant_default", "item_id", "is_default"),
    )
    
class ItemStoreLink(db.Model):
    __tablename__ = "item_store_links"
    id = db.Column(db.Integer, primary_key=True)
    variant_id = db.Column(
        db.Integer,
        db.ForeignKey("item_variants.id", ondelete="CASCADE"),
        nullable=False
    )
    store_id = db.Column(
        db.Integer,
        db.ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False
    )
    external_item_id = db.Column(db.String(150))
    affiliate_url = db.Column(db.Text, nullable=False)
    price = db.Column(db.Numeric(10, 2))
    old_price = db.Column(db.Numeric(10, 2))
    currency = db.Column(db.String(3))
    availability = db.Column(db.String(32), index=True)
    last_checked_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    variant = db.relationship("ItemVariant", back_populates="store_links")
    store = db.relationship("Store", back_populates="item_links")
    __table_args__ = (
        db.UniqueConstraint(
            "variant_id", "store_id",
            name="uq_variant_store"
        ),
        db.Index("ix_item_store_price", "price"),
        db.Index("ix_item_store_variant", "variant_id"),
        db.Index("ix_item_store_store", "store_id"),
    )

class ItemImage(db.Model):
    __tablename__ = "item_images"
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey("item_variants.id", ondelete="CASCADE"), nullable=True)
    image_url = db.Column(db.Text, nullable=False)  # relative path, e.g. 'static/images/gal-f07_1.png'
    position = db.Column(db.Integer, default=0)  # order of images
    item = db.relationship("Item", back_populates="images")
    variant = db.relationship("ItemVariant", back_populates="images")
    def __repr__(self):
        return f"<ItemImage {self.image_url}>"
class ItemSpecification(db.Model):
    __tablename__ = "item_specifications"
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)
    category = db.Column(db.String(100))  # optional, e.g., 'display', 'battery', notes
    spec_json = db.Column(db.JSON)  # store the whole dict
    item = db.relationship("Item", back_populates="specifications")
    __table_args__ = (
        db.Index("ix_item_specs_item", "item_id"),
    )
    def __repr__(self):
        return f"<ItemSpecification {self.category}>"
# LIKES & COMMENTS & VIEWS MODELS
# ==================== REACTIONS (LIKE / DISLIKE / FUTURE TYPES) ====================
class Reaction(db.Model):
    __tablename__ = "reactions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)  # 'article' or 'item'
    target_id = db.Column(db.Integer, nullable=False)       # ID of the target (polymorphic)
    type = db.Column(db.String(20), nullable=False)         # 'like', 'dislike', etc.
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    @property
    def target(self):
        return self.article or self.item or self.comment
    user = db.relationship("User", back_populates="reactions")
    # Reaction model
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
# ==================== COMMENTS ====================
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)  # 'article' or 'item'
    target_id = db.Column(db.Integer, nullable=False)       # ID of the target (polymorphic)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    # Parent comment for replies
    parent_id = db.Column(db.Integer, db.ForeignKey("comments.id", ondelete="CASCADE"), nullable=True)
    sentiment = db.Column(db.String(20), nullable=True)
    confidence = db.Column(db.Float, nullable=True)
    likes_count = db.Column(db.Integer, default=0)
    dislikes_count = db.Column(db.Integer, default=0)
    @property
    def target(self):
        return self.article or self.item
    # Relationships
    user = db.relationship("User", back_populates="comments")
    parent = db.relationship("Comment", remote_side=[id], back_populates="replies")
    replies = db.relationship(
        "Comment",
        back_populates="parent",
        cascade="all, delete-orphan"
    )
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
    reactions  = db.relationship(
        "Reaction",
        primaryjoin="and_(foreign(Reaction.target_id) == Comment.id, Reaction.target_type == 'comment')",
        back_populates="comment",
        viewonly=True,
        lazy="selectin"
    )
    __table_args__ = (
        db.Index("idx_comments_target", "target_type", "target_id"),
        db.CheckConstraint(
            "target_type IN ('article', 'item')",
            name="ck_comment_target_type"
        ),
    )
    def __repr__(self):
        return (
            f"<Comment id={self.id} "
            f"user={self.user_id} "
            f"{self.target_type}:{self.target_id} "
            f"parent={self.parent_id}>"
        )
# ==================== VIEWS ====================
class View(db.Model):
    __tablename__ = "views"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True)  # anonymous possible
    target_type = db.Column(db.String(50), nullable=False)  # 'article' or 'item'
    target_id = db.Column(db.Integer, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)  # store IPv4 or IPv6
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
        db.CheckConstraint(
            "(user_id IS NOT NULL AND ip_address IS NULL) OR "
            "(user_id IS NULL AND ip_address IS NOT NULL)",
            name="ck_view_one_identity"
        ),
        db.UniqueConstraint(
            "user_id", "ip_address", "target_type", "target_id",
            name="unique_view"
        ),
        db.CheckConstraint(
            "target_type IN ('article', 'item')",
            name="ck_view_target_type"
        ),
    )
    def __repr__(self):
        viewer = f"user={self.user_id}" if self.user_id else f"ip={self.ip_address}"
        return f"<View {viewer} {self.target_type}:{self.target_id}>"
# SAVES & BOOKMARKS
class Save(db.Model):
    __tablename__ = "saves"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    target_type = db.Column(db.String(50), nullable=False)  # article | item
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
    __table_args__ = (
        db.UniqueConstraint("user_id", "target_type", "target_id", name="uq_user_save"),
        db.Index("ix_save_target", "target_type", "target_id"),
        db.CheckConstraint(
            "target_type IN ('article', 'item')",
            name="ck_save_target_type"
        ),
    )
    user = db.relationship("User", back_populates="saves")
    
    def __repr__(self):
        return f"<Save user={self.user_id} {self.target_type}:{self.target_id}>"
# PRODUCT CLICK
class ItemClick(db.Model):
    __tablename__ = "item_clicks"
    id = db.Column(db.Integer, primary_key=True)
    item_store_link_id = db.Column(
        db.Integer,
        db.ForeignKey("item_store_links.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    ip_address = db.Column(db.String(45))   # IPv6 safe
    user_agent = db.Column(db.Text)
    referrer = db.Column(db.Text)
    country = db.Column(db.String(50))
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        index=True
    )
    user = db.relationship("User", back_populates="item_clicks")
    item_store_link = db.relationship("ItemStoreLink")
    __table_args__ = (
        db.Index("ix_item_click_link", "item_store_link_id"),
        db.Index("ix_item_click_user", "user_id"),
    )
    def __repr__(self):
        return (
            f"<ItemClick id={self.id} "
            f"link={self.item_store_link_id} "
            f"user={self.user_id} "
            f"ip={self.ip_address}>"
        )
# ================= USER INTEREST =================
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
# ================= USER ENTITY INTEREST =================
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
        db.CheckConstraint(
            "(brand_id IS NOT NULL) OR (category_id IS NOT NULL) OR (topic_id IS NOT NULL)",
            name="ck_entity_reference"
        ),
        db.Index("ix_user_entity_interest_ref", "brand_id", "category_id", "topic_id"),
    )
# ==================================================================
class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
