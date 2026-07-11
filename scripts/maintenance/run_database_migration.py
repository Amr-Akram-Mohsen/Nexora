import os
import sys
import logging
from sqlalchemy import text, select

# Ensure we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core import create_app
from app.core.extensions import db
from app.domains.taxonomy.models import Entity, Brand
from app.domains.relationships import ContentEntity
from app.shared.utils.slug import generate_slug

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    app = create_app()
    with app.app_context():
        logger.info("Starting database migration...")
        
        # 1. Migrate Brands to Entities
        logger.info("Migrating legacy brands to entities...")
        # Get all brands to ensure they exist as Entities
        brands = db.session.execute(select(Brand)).scalars().all()
        for brand in brands:
            Entity.get_or_create(
                name=brand.name,
                session=db.session,
                entity_type="brand",
                provider="legacy"
            )
        db.session.commit()
        
        # 2. Migrate content_brands to ContentEntity
        logger.info("Migrating content_brands to ContentEntity...")
        try:
            # We use raw SQL because the SQLAlchemy models for these tables were deleted
            result = db.session.execute(text("SELECT content_id, brand_id FROM content_brands"))
            rows = result.fetchall()
            
            for content_id, brand_id in rows:
                brand = db.session.get(Brand, brand_id)
                if not brand:
                    continue
                
                entity = Entity.get_by_slug(brand.slug, db.session)
                if not entity:
                    continue
                
                ContentEntity.get_or_create(
                    content_id=content_id,
                    entity_id=entity.id,
                    session=db.session,
                    origin="legacy_brand",
                    relevance_score=1.0,
                    confidence=1.0
                )
            
            db.session.commit()
            logger.info(f"Successfully migrated {len(rows)} brand associations.")
        except Exception as e:
            db.session.rollback()
            logger.warning(f"Could not migrate content_brands (maybe table doesn't exist?): {e}")

        # 3. Migrate content_topics to ContentEntity
        logger.info("Migrating content_topics to ContentEntity...")
        try:
            # Assuming there is a topics table as well
            result = db.session.execute(text("""
                SELECT cta.content_id, t.name 
                FROM content_topics cta
                JOIN topics t ON cta.topic_id = t.id
            """))
            rows = result.fetchall()
            
            for content_id, topic_name in rows:
                entity = Entity.get_or_create(
                    name=topic_name,
                    session=db.session,
                    entity_type="topic",
                    provider="legacy"
                )
                
                ContentEntity.get_or_create(
                    content_id=content_id,
                    entity_id=entity.id,
                    session=db.session,
                    origin="legacy_topic",
                    relevance_score=1.0,
                    confidence=1.0
                )
                
            db.session.commit()
            logger.info(f"Successfully migrated {len(rows)} topic associations.")
        except Exception as e:
            db.session.rollback()
            logger.warning(f"Could not migrate content_topics (maybe table doesn't exist?): {e}")

        # 4. Drop Legacy Tables
        logger.info("Dropping legacy tables...")
        try:
            db.session.execute(text("DROP TABLE IF EXISTS content_brands;"))
            db.session.execute(text("DROP TABLE IF EXISTS content_topics;"))
            db.session.commit()
            logger.info("Legacy tables dropped successfully.")
        except Exception as e:
            db.session.rollback()
            logger.warning(f"Error dropping legacy tables: {e}")

        logger.info("Database migration completed!")

if __name__ == "__main__":
    migrate_database()
