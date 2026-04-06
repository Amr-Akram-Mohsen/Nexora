# app/utils/seeder.py
"""
Seeding script for Sections and Categories.
Ensures the database is ready for the scrapers to work.
"""
from app.models import db, Section, Category
import logging

logger = logging.getLogger(__name__)

# Predefined Sections
SECTIONS = [
    {"name": "News",           "slug": "news",        "desc": "Latest technology, perfume, and fashion updates."},
    {"name": "Reviews",        "slug": "reviews",     "desc": "Hands-on testing and expert opinions on new products."},
    {"name": "Tutorials",      "slug": "tutorials",   "desc": "How-to guides, programming tips, and fashion advice."},
    {"name": "Trends",         "slug": "trends",      "desc": "Market movements and what's hot right now."},
    {"name": "Community",      "slug": "community",   "desc": "The voice of the users: feedback from Reddit and social media."},
]

# Predefined Categories (High Level)
CATEGORIES = [
    {"name": "Electronics",    "slug": "electronics", "parent": None},
    {"name": "Perfumes",       "slug": "perfumes",    "parent": None},
    {"name": "Accessories",    "slug": "accessories", "parent": None},
    {"name": "General",        "slug": "general",     "parent": None},
]


def seed_db():
    """Seed the database with initial metadata."""
    logger.info("[Seeder] Starting DB seed...")

    # 1. Seed Sections
    for s_data in SECTIONS:
        section = Section.query.filter_by(slug=s_data["slug"]).first()
        if not section:
            section = Section(
                name=s_data["name"],
                slug=s_data["slug"],
                description=s_data["desc"],
                allowed_filters=["brand", "topic"]
            )
            db.session.add(section)
            logger.info(f"[Seeder]   + Section: {s_data['name']}")
    db.session.flush()

    # 2. Seed Categories
    for c_data in CATEGORIES:
        category = Category.query.filter_by(slug=c_data["slug"]).first()
        if not category:
            category = Category(
                name=c_data["name"],
                slug=c_data["slug"],
                is_active=True
            )
            db.session.add(category)
            logger.info(f"[Seeder]   + Category: {c_data['name']}")

    try:
        db.session.commit()
        logger.info("[Seeder] Seed complete!")
    except Exception:
        db.session.rollback()
        logger.exception("[Seeder] Seed failed")
