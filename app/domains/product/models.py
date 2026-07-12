from functools import cached_property
from app.core.extensions import db
from app.shared.sanitizer import sanitize_json
from app.domains.relationships import content_products
# ==================== ASSOCIATION TABLES ====================
from sqlalchemy.dialects.postgresql import TSVECTOR

class Store(db.Model):
    __tablename__ = "stores"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    website = db.Column(db.Text, nullable=False)
    country = db.Column(db.String(50))
    currency = db.Column(db.String(10))
    affiliate_network = db.Column(db.String(100))

    network_slug = db.Column(db.String(100), nullable=True, index=True)
    api_enabled = db.Column(db.Boolean, default=False)
    feed_enabled = db.Column(db.Boolean, default=False)

    logo_url = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    product_links = db.relationship(
        "ProductStoreLink", back_populates="store", cascade="all, delete-orphan"
    )


# ==================== CONSTANTS ====================

# Priority order for variant attribute groups in the selector UI
_VARIANT_ATTR_PRIORITY = {
    "color": 1,
    "storage": 2,
    "ram": 3,
    "size": 4,
    "volume": 5,
}

# ==================== PRODUCT MODELS ====================
class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), nullable=False, unique=True)
    description = db.Column(db.Text)
    rating = db.Column(db.Float)

    review_count = db.Column(db.Integer)

    product_type = db.Column(db.String(50), nullable=True)

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), index=True)
    
    like_count = db.Column(db.Integer, nullable=False, default=0)
    dislike_count = db.Column(db.Integer, nullable=False, default=0)
    share_count = db.Column(db.Integer, nullable=False, default=0)
    save_count = db.Column(db.Integer, nullable=False, default=0)
    comment_count = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)
    click_count = db.Column(db.Integer, default=0)

    searchable_attributes = db.Column(db.JSON)

    search_text = db.Column(
        db.Text
    )

    search_vector = db.Column(
        TSVECTOR
    )

    category = db.relationship("Category", back_populates="products")
    brand = db.relationship("Brand", back_populates="products")

    linked_contents = db.relationship(
        "Content", secondary=content_products, back_populates="linked_products"
    )

    variants = db.relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    images = db.relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.position",
        lazy="selectin",
        overlaps="images",
    )
    specifications = db.relationship(
        "ProductSpecification",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Reactions, Comments, Views
    reactions = db.relationship(
        "Reaction",
        primaryjoin="and_(foreign(Reaction.target_id)==Product.id, Reaction.target_type=='product')",
        back_populates="product",
        viewonly=True,
        lazy="noload",
    )
    comments = db.relationship(
        "Comment",
        primaryjoin="and_(foreign(Comment.target_id)==Product.id, Comment.target_type=='product')",
        back_populates="product",
        viewonly=True,
        lazy="noload",
    )
    views = db.relationship(
        "View",
        primaryjoin="and_(foreign(View.target_id)==Product.id, View.target_type=='product')",
        back_populates="product",
        viewonly=True,
        lazy="noload",
    )

    def set_default_variant(self):
        if not self.variants:
            return
        if not any(v.is_default for v in self.variants):
            self.variants[0].is_default = True

    @property
    def title(self):
        return self.name

    @cached_property
    def image_url(self):
        """URL of the first product image. Cached for the lifetime of this instance."""
        return self.images[0].image_url if self.images else None

    @cached_property
    def default_variant(self):
        """The default variant (is_default=True), or first variant, or None."""
        return next(
            (v for v in self.variants if v.is_default),
            self.variants[0] if self.variants else None,
        )

    @cached_property
    def price(self):
        """Price of the default variant."""
        return self.default_variant.price if self.default_variant else None

    @cached_property
    def min_price(self):
        """Lowest price across all variants."""
        prices = [v.price for v in self.variants if v.price is not None]
        return min(prices) if prices else None

    @property
    def has_variants(self):
        return len(self.variants) > 1

    @cached_property
    def store_links(self):
        """Active store links for the default variant."""
        if not self.default_variant:
            return []
        return [link for link in self.default_variant.store_links if link.is_active]

    @staticmethod
    def pick_keys(d, keys):
        if not isinstance(d, dict):
            return None
        norm_d = {str(k).lower().strip(): v for k, v in d.items()}
        result = {}
        for key in keys:
            norm_key = str(key).lower().strip()
            if norm_key in norm_d and norm_d[norm_key] is not None:
                result[key] = norm_d[norm_key]
        return result or None

    @staticmethod
    def get_specifications(result):
        return {k: v for k, v in result.items() if v}

    @property
    def full_details(self):
        return {
            spec.category: sanitize_json(spec.spec_json)
            for spec in self.specifications
            if isinstance(spec.spec_json, dict)
        }

    @cached_property
    def structured_details(self):
        data = self.full_details
        if self.product_type == "technology":
            return {
                "highlights": self.pick_keys(
                    {
                        **data.get("display", {}),
                        **data.get("platform", {}),
                        **data.get("battery", {}),
                    },
                    ["size", "chipset", "type"],
                ),
                "quick_details": data,
                "groups": data,
            }
        elif self.product_type == "perfumes":
            fp = data.get("fragrance_profile", {})
            return {
                "scent": {
                    "top": fp.get("top_notes"),
                    "heart": fp.get("heart_notes"),
                    "base": fp.get("base_notes"),
                },
                "meta": self.pick_keys(fp, ["concentration", "scent_family"]),
                "performance": data.get("performance", {}),
                "quick_details": data.get("performance", {}),
                "groups": data,
            }
        elif self.product_type == "accessories":
            return {
                "materials": data.get("material_build", {}),
                "dimensions": data.get("dimensions", {}),
                "movement": data.get("movement", {}),
                "quick_details": data.get("movement", {}),
                "groups": data,
            }
        return {"quick_details": data, "groups": data}

    def get_product_schema(self, request_url):
        schema = {
            "@context": "https://schema.org/",
            "@type": "Product",
            "name": self.name,
            "description": self.description,
            "brand": {"@type": "Brand", "name": self.brand.name if self.brand else "Unknown"},
            "category": self.category.name if self.category else "Unknown",
            "url": request_url,
            "sku": self.default_variant.sku if self.default_variant else None,
        }
        if self.images:
            schema["image"] = [img.image_url for img in self.images]
        if self.store_links:
            offers = []
            for link in self.store_links:
                offers.append(
                    {
                        "@type": "Offer",
                        "price": float(link.price),
                        "priceCurrency": link.currency,
                        "availability": f"https://schema.org/{link.availability or 'InStock'}",
                        "url": link.affiliate_url,
                    }
                )
            schema["offers"] = offers
        return schema

    @cached_property
    def quick_details(self):
        """Flat list of {group, label, value} dicts for the quick-details grid."""
        return self._quick_details(self.structured_details.get("quick_details", {}))

    def _quick_details(self, details=None, parent=""):
        if not isinstance(details, dict):
            return []
        rows = []
        for key, value in details.items():
            label = str(key).replace("_", " ").title()
            current_group = parent or label
            if isinstance(value, dict):
                rows.extend(self._quick_details(value, current_group))
            else:
                rows.append({"group": parent, "label": label, "value": value})
        return rows
    
    @cached_property
    def variant_groups(self):
        """Attribute→sorted-values mapping used by the variant selector.

        Groups are ordered by the canonical priority list so Color always
        appears before Storage, RAM, Size, Volume, etc.
        Cached: computed once per Product instance.
        """
        groups: dict[str, set] = {}
        for variant in self.variants:
            for key, value in (variant.attributes or {}).items():
                if value:
                    groups.setdefault(key, set()).add(value)

        return dict(
            sorted(
                {k: sorted(v) for k, v in groups.items()}.items(),
                key=lambda x: _VARIANT_ATTR_PRIORITY.get(x[0], 999),
            )
        )



    __table_args__ = (
        db.Index("ix_products_slug", "slug"),
        db.Index("ix_products_brand_category", "brand_id", "category_id"),
        db.Index("ix_products_type_created", "product_type", "created_at"),
        db.Index("ix_products_category_created", "category_id", "created_at"),
        db.Index(
            "ix_products_search_vector",
            "search_vector",
            postgresql_using="gin"
        )
    )

    def __repr__(self):
        return f"<Product {self.name}>"


class ProductVariant(db.Model):
    __tablename__ = "product_variants"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    title = db.Column(db.String(200), nullable=True)
    sku = db.Column(db.String(100), unique=True, nullable=True)
    attributes = db.Column(db.JSON)
    is_default = db.Column(db.Boolean, default=False)
    price = db.Column(db.Numeric(10, 2), index=True)
    old_price = db.Column(db.Numeric(10, 2))
    currency = db.Column(db.String(3))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    product = db.relationship("Product", back_populates="variants")
    images = db.relationship(
        "ProductImage", back_populates="variant", cascade="all, delete-orphan"
    )
    store_links = db.relationship(
        "ProductStoreLink",
        back_populates="variant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def normalize_attributes(self):
        if not self.attributes:
            return
        self.attributes = {
            str(k).lower().strip(): str(v).strip() for k, v in self.attributes.items()
        }

    def display_name(self):
        if self.title:
            return self.title
        if self.attributes:
            return " / ".join(
                f"{k.capitalize()}: {v}" for k, v in self.attributes.items()
            )
        return "Default"

    __table_args__ = (
        db.Index("ix_product_variant_product", "product_id"),
        db.Index("ix_product_variant_default", "product_id", "is_default"),
    )


class ProductStoreLink(db.Model):
    __tablename__ = "product_store_links"
    id = db.Column(db.Integer, primary_key=True)
    variant_id = db.Column(
        db.Integer,
        db.ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
    )
    store_id = db.Column(
        db.Integer, db.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    external_product_id = db.Column(db.String(150))

    original_url = db.Column(db.Text, nullable=True)

    program_name = db.Column(db.String(100), nullable=True, index=True)

    merchant_category = db.Column(db.String(255), nullable=True)

    commission_rate = db.Column(db.Numeric(5, 2), nullable=True)

    deeplink_generated_at = db.Column(db.DateTime, nullable=True)

    last_synced_at = db.Column(db.DateTime, nullable=True)

    tracking_code = db.Column(db.String(255), nullable=True)

    network_metadata = db.Column(db.JSON, nullable=True)

    affiliate_url = db.Column(db.Text, nullable=False)
    price = db.Column(db.Numeric(10, 2))
    old_price = db.Column(db.Numeric(10, 2))
    currency = db.Column(db.String(3))
    availability = db.Column(db.String(32), index=True)
    last_checked_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    variant = db.relationship("ProductVariant", back_populates="store_links")
    store = db.relationship("Store", back_populates="product_links")

    __table_args__ = (
        db.UniqueConstraint("variant_id", "store_id", name="uq_product_variant_store"),
        db.Index("ix_product_store_price", "price"),
        db.Index("ix_product_store_variant", "variant_id"),
        db.Index("ix_product_store_store", "store_id"),
        db.Index("ix_product_store_program", "program_name"),
        db.Index("ix_product_store_external", "external_product_id"),
    )


class ProductImage(db.Model):
    __tablename__ = "product_images"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    variant_id = db.Column(
        db.Integer, db.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True
    )
    image_url = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, default=0)
    product = db.relationship("Product", back_populates="images")
    variant = db.relationship("ProductVariant", back_populates="images")

    def __repr__(self):
        return f"<ProductImage {self.image_url}>"


class ProductSpecification(db.Model):
    __tablename__ = "product_specifications"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    category = db.Column(db.String(100))
    spec_json = db.Column(db.JSON)
    product = db.relationship("Product", back_populates="specifications")
    __table_args__ = (db.Index("ix_product_specs_product", "product_id"),)

    def __repr__(self):
        return f"<ProductSpecification {self.category}>"
