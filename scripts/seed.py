# app/utils/seeder.py
"""
Seeding script for Sections, Categories, Topics, and Brands.
Ensures the database is ready for the ingestion engine to work.
Uses taxonomy_v2.json as the source of truth.
PERFORMS A NUCLEAR RESET: Wipes all tables and resets auto-increment counters to 1.
"""
import json
import os
import logging
from app.core.extensions import db
from app.shared.utils.slug import generate_slug, normalize_name

# Import ALL models to ensure db.drop_all() covers every table
from app.domains.system.models import (
    Section, Category, Topic, Brand,
    GenderFacet, IntentFacet, PriceTierFacet, AttributeFacet
)

logger = logging.getLogger(__name__)

TAXONOMY_PATH = os.path.join("app", "shared", "constants", "taxonomy_v2.json")

def load_taxonomy():
    if not os.path.exists(TAXONOMY_PATH):
        logger.error(f"[Seeder] Taxonomy file not found at {TAXONOMY_PATH}")
        return None
    with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def seed_db():
    """Seed the database with initial metadata from taxonomy_v2.json after a NUCLEAR RESET."""
    logger.info("[Seeder] !!! NUCLEAR RESET INITIATED !!!")
    
    taxonomy = load_taxonomy()
    if not taxonomy:
        return

    try:
        # 1. Nuclear Reset: Drop and Create all tables
        # This is the most reliable way to reset auto-increment to 1 in SQLite/Postgres
        db.drop_all()
        db.create_all()
        logger.info("[Seeder] All tables dropped and recreated. Counters reset to 1.")

        # 2. Seed Sections
        for s_data in taxonomy.get("sections", []):
            slug = generate_slug(s_data["name"])
            section = Section(
                name=s_data["name"],
                slug=slug,
                description=s_data["description"],
                allowed_filters=[
                    "brand",
                    "topic",
                    "price_tier",
                    "intent",
                    "gender",
                    "attributes"
                ]
            )
            db.session.add(section)
            logger.info(f"[Seeder]   + Section: {s_data['name']}")
        db.session.flush()

        # 3. Seed Categories (Hierarchical)
        for c_data in taxonomy.get("categories", []):
            parent_slug = generate_slug(c_data["name"])
            parent = Category(
                name=c_data["name"],
                slug=parent_slug,
                is_leaf=c_data.get("is_leaf", False),
                normalized_name=normalize_name(c_data["name"]),
                is_active=True
            )
            db.session.add(parent)
            db.session.flush() 
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

        # 4. Seed Topics
        for t_data in taxonomy.get("topics", []):
            topic = Topic(
                name=t_data["name"],
                slug=generate_slug(t_data["name"]),
                normalized_name=normalize_name(t_data["name"]),
            )
            db.session.add(topic)
            logger.info(f"[Seeder]   + Topic: {t_data['name']}")

        db.session.commit()

        # 5. Seed Brands
        for b_data in taxonomy.get("brands", []):
            brand = Brand(
                name=b_data["name"],
                slug=generate_slug(b_data["name"]),
                normalized_name=normalize_name(b_data["name"]),
            )
            db.session.add(brand)
            logger.info(f"[Seeder]   + Brand: {b_data['name']}")
        
        db.session.commit()

        # 6. Seed Facets
        facets = taxonomy.get("facets", {})

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
                category_obj = Category.query.filter_by(
                    normalized_name=normalize_name(attr["category"])
                ).first()

            db.session.add(AttributeFacet(
                name=attr["name"],
                slug=generate_slug(attr["name"]),
                category_id=category_obj.id
            ))
            logger.info(f"[Seeder] [Facets]   + Attributes: {attr['name']}")

        db.session.commit()


        logger.info("[Seeder] Seed complete! Database is now clean and taxonomy is active.")
    except Exception:
        db.session.rollback()
        logger.exception("[Seeder] Nuclear seed failed")
