# app/utils/seeder.py
"""
Seeding script for Sections, Categories, and Topics.
Ensures the database is ready for the scrapers to work.
"""
from app.models import db, Section, Category, Topic
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

# Predefined Categories (With Parent Support)
CATEGORIES = [
    # Top Level
    {"name": "Electronics",    "slug": "electronics", "parent": None},
    {"name": "Perfumes",       "slug": "perfumes",    "parent": None},
    {"name": "Accessories",    "slug": "accessories", "parent": None},
    {"name": "General",        "slug": "general",     "parent": None},
    
    # Sub-categories (Electronics)
    {"name": "Smartphones",    "slug": "smartphones", "parent": "electronics"},
    {"name": "Laptops",        "slug": "laptops",     "parent": "electronics"},
    {"name": "Smartwatches",   "slug": "smartwatches","parent": "electronics"},
    {"name": "Cameras",        "slug": "cameras",     "parent": "electronics"},

    # Sub-categories (Perfumes)
    {"name": "Men's Perfumes", "slug": "mens-perfume", "parent": "perfumes"},
    {"name": "Women's Perfumes", "slug": "womens-perfume", "parent": "perfumes"},
    {"name": "Niche & Artisanal", "slug": "niche-perfume", "parent": "perfumes"},
    {"name": "Oud & Oriental", "slug": "oud-perfume", "parent": "perfumes"},

    # Sub-categories (Accessories)
    {"name": "Luxury Watches", "slug": "luxury-watches", "parent": "accessories"},
    {"name": "Sunglasses", "slug": "sunglasses", "parent": "accessories"},
    {"name": "Jewelry", "slug": "jewelry", "parent": "accessories"},
    {"name": "Bags", "slug": "bags", "parent": "accessories"},
]

# Topics grouped by 'type'
TOPICS = [
    # Intent & Use-Case (The 'Why')
    {"name": "Gaming",         "slug": "gaming",        "type": "intent",    "featured": True},
    {"name": "Home Office",    "slug": "home-office",   "type": "intent",    "featured": True},
    {"name": "Photography",    "slug": "photography",   "type": "intent",    "featured": False},
    {"name": "Fitness",        "slug": "fitness",       "type": "intent",    "featured": False},
    {"name": "Travel Gear",    "slug": "travel-gear",        "type": "intent",    "featured": False},
    
    # Price-Point (The 'How Much')
    {"name": "Budget Picks",   "slug": "budget-picks",        "type": "price",     "featured": True},
    {"name": "Mid-Range",      "slug": "mid-range",     "type": "price",     "featured": False},
    {"name": "Premium Luxury", "slug": "premium-luxury",        "type": "price",     "featured": False},
    {"name": "Best Value",     "slug": "best-value",         "type": "price",     "featured": True},
    
    # Editorial (The 'Curation')
    {"name": "Buying Guides",  "slug": "buying-guides", "type": "editorial", "featured": True},
    {"name": "Gift Ideas",     "slug": "gift-ideas",    "type": "editorial", "featured": True},
    {"name": "Editor's Choice","slug": "editors-choice","type": "editorial", "featured": True},
    {"name": "Top 10 Lists",   "slug": "top-10",        "type": "editorial", "featured": False},
    
    # Perfume Specific (Cross-Category Intent)
    {"name": "Summer Scents",  "slug": "summer-scents",        "type": "perfume",   "featured": False},
    {"name": "Long-Lasting",   "slug": "long-lasting",  "type": "perfume",   "featured": False},
    {"name": "Date Night",     "slug": "date-night",    "type": "perfume",   "featured": False},
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
                allowed_filters=["brand", "topic", "category"]
            )
            db.session.add(section)
            logger.info(f"[Seeder]   + Section: {s_data['name']}")
    db.session.flush()

    # 2. Seed Categories (Hierarchical)
    # First pass: Create all categories
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
    db.session.flush()

    # Second pass: Associate parents
    for c_data in CATEGORIES:
        if c_data["parent"]:
            cat = Category.query.filter_by(slug=c_data["slug"]).first()
            parent = Category.query.filter_by(slug=c_data["parent"]).first()
            if cat and parent:
                cat.parent_id = parent.id
                logger.info(f"[Seeder]   Linked {cat.name} -> {parent.name}")

    # 3. Seed Topics
    for t_data in TOPICS:
        topic = Topic.query.filter_by(slug=t_data["slug"]).first()
        if not topic:
            topic = Topic(
                name=t_data["name"],
                slug=t_data["slug"],
                type=t_data["type"],
                is_featured=t_data["featured"],
                is_active=True
            )
            db.session.add(topic)
            logger.info(f"[Seeder]   + Topic: [{t_data['type']}] {t_data['name']}")

    try:
        db.session.commit()
        logger.info("[Seeder] Seed complete!")
    except Exception:
        db.session.rollback()
        logger.exception("[Seeder] Seed failed")
