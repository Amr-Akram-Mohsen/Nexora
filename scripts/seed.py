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
from app.domains.user.models import User
from app.domains.article.models import Article
from app.domains.item.models import Item, Store, ItemStoreLink
from app.domains.core.models import Section, Category, Topic, Brand
from app.domains.interaction.models import Comment, Reaction, View, Save, ItemClick
from app.domains.external.models import LastAPIFetch, APIUsage

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
                allowed_filters=["brand", "topic", "category"]
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
            slug = generate_slug(t_data["name"])
            topic = Topic(
                name=t_data["name"],
                slug=slug,
                type=t_data.get("type", "intent"),
                normalized_name=normalize_name(t_data["name"]),
                is_active=True
            )
            db.session.add(topic)
            logger.info(f"[Seeder]   + Topic: {t_data['name']}")

        db.session.commit()
        logger.info("[Seeder] Seed complete! Database is now clean and taxonomy is active.")
    except Exception:
        db.session.rollback()
        logger.exception("[Seeder] Nuclear seed failed")
