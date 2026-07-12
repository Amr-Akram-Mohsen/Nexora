# scripts/seed.py
"""
Seeding script for Sections, Categories, Topics, Brands, Facets, and Sources.

⚠️ This script DOES NOT reset the database.
It assumes tables are already created (via migrations) and empty (or safe to insert into).

Use Supabase SQL Editor for full resets.
"""
import logging
from app.core.extensions import db
from app.shared.utils.slug import generate_slug, normalize_name
from app.shared.constants.taxonomy import TAXONOMY
from sqlalchemy import select

from app.domains.taxonomy.models import (
    Section, Category, Brand, Source,
    GenderFacet, IntentFacet, PriceTierFacet, AttributeFacet
)

logger = logging.getLogger(__name__)

def seed_db():
    """Seed the database with initial metadata from TAXONOMY"""
    # Import EVERY model module to ensure db.metadata is 100% complete

    logger.info("[Seeder] Starting database seed...")
    
    if not TAXONOMY:
        logger.warning("[Seeder] TAXONOMY is empty. Aborting.")
        return

    try:
        # 1. Seed Sections
        for s_data in TAXONOMY.get("sections", []):
            slug = generate_slug(s_data["name"])
            section = Section(
                name=s_data["name"],
                slug=slug,
                description=s_data["description"],
                allowed_filters=[
                    "category",
                    "brand",
                    "entity",
                    "price_tier",
                    "intent",
                    "gender",
                    "attributes",
                    "type"
                ]
            )
            db.session.add(section)
            logger.info(f"[Seeder]   + Section: {s_data['name']}")

        # 2. Seed Categories (Hierarchical)
        for c_data in TAXONOMY.get("categories", []):
            parent_slug = generate_slug(c_data["name"])
            parent = Category(
                name=c_data["name"],
                slug=parent_slug,
                is_leaf=c_data.get("is_leaf", False),
                normalized_name=normalize_name(c_data["name"]),
                is_active=True
            )
            db.session.add(parent)
            logger.info(f"[Seeder]   + Category Cluster: {c_data['name']}")

            # Seed children
            for child_data in c_data.get("children", []):
                child_slug = generate_slug(child_data["name"])
                child = Category(
                    name=child_data["name"],
                    slug=child_slug,
                    parent_id=parent.id,
                    is_leaf=child_data.get("is_leaf", True),
                    normalized_name=normalize_name(child_data["name"]),
                    is_active=True
                )
                db.session.add(child)
                logger.info(f"[Seeder]     -> Leaf: {child_data['name']}")


        # 3. Seed Brands
        for b_data in TAXONOMY.get("brands", []):
            brand = Brand(
                name=b_data["name"],
                slug=generate_slug(b_data["name"]),
                normalized_name=normalize_name(b_data["name"]),
            )
            db.session.add(brand)
            logger.info(f"[Seeder]   + Brand: {b_data['name']}")
        
        # 4. Seed Facets
        facets = TAXONOMY.get("facets", {})

        # Gender
        for g in facets.get("gender", []):
            db.session.add(GenderFacet(
                name=g["name"],
                slug=generate_slug(g["name"])
            ))
            logger.info(f"[Seeder] [Facets]   + Gender: {g['name']}")

        # Intent
        for i in facets.get("intent", []):
            db.session.add(IntentFacet(
                name=i["name"],
                slug=generate_slug(i["name"])
            ))
            logger.info(f"[Seeder] [Facets]   + Intent: {i['name']}")

        # Price Tier
        for p in facets.get("price_tier", []):
            db.session.add(PriceTierFacet(
                name=p["name"],
                slug=generate_slug(p["name"])
            ))
            logger.info(f"[Seeder] [Facets]   + Price Tier: {p['name']}")

        # Attributes
        for attr in facets.get("attributes", []):
            category_obj = None

            if attr.get("category"):
                category_obj = db.session.scalar(
                    select(Category).filter_by(
                        normalized_name=normalize_name(attr["category"])
                    )
                )

            db.session.add(AttributeFacet(
                name=attr["name"],
                slug=generate_slug(attr["name"]),
                category_id=category_obj.id if category_obj else None
            ))
            logger.info(f"[Seeder] [Facets]   + Attributes: {attr['name']}")
        
        from app.shared.constants.taxonomy import TRUSTED_SOURCES
        # 5. Seed Trusted Sources
        for s in TRUSTED_SOURCES:
            db.session.add(Source(
                name=s["name"],
                slug=generate_slug(s["name"]),
                domain=s["domain"],
                is_active=True,
                authority_score=s.get("score", 50)
            ))
            logger.info(f"[Seeder]   + Source: {s['name']}")
        
        db.session.commit()
        logger.info("[Seeder] Seed complete!")
    except Exception as e:
        db.session.rollback()
        logger.exception("[Seeder] seed failed")
        raise e
