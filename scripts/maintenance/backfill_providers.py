# scripts/maintenance/backfill_providers.py
import sys
import os
from urllib.parse import urlparse

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from dotenv import load_dotenv
load_dotenv()

from main import app
from app.core.extensions import db
from app.domains.taxonomy.models import Source
from app.domains.content.models import Content, Article, Video, Post
from app.domains.item.models import Item
from app.domains.relationships import ArticleSource
from app.shared.utils.slug import generate_slug
from app.shared.constants.taxonomy import TRUSTED_SOURCES

DEFAULT_PLATFORM_SOURCES = {
    "youtube": {"name": "YouTube", "domain": "youtube.com", "score": 95},
    "reddit": {"name": "Reddit", "domain": "reddit.com", "score": 80},
    "rss": {"name": "RSS Feeds", "domain": "rss.com", "score": 75},
    "newsapi": {"name": "NewsAPI", "domain": "newsapi.org", "score": 70},
    "gnews": {"name": "GNews", "domain": "gnews.io", "score": 70},
    "aliexpress": {"name": "AliExpress", "domain": "aliexpress.com", "score": 85},
    "amazon": {"name": "Amazon", "domain": "amazon.com", "score": 90},
    "noon": {"name": "Noon", "domain": "noon.com", "score": 85},
}

def backfill_providers():
    with app.app_context():
        print("--- Seeding/Ensuring Default Platform Sources ---")
        for slug, cfg in DEFAULT_PLATFORM_SOURCES.items():
            source = Source.query.filter_by(slug=slug).first()
            if not source:
                source = Source(
                    name=cfg["name"],
                    slug=slug,
                    domain=cfg["domain"],
                    authority_score=cfg["score"],
                    is_active=True
                )
                db.session.add(source)
                print(f"Created platform source: {cfg['name']} ({slug})")
        db.session.commit()

        # Seed any other trusted sources from constant
        print("\n--- Seeding/Ensuring Trusted Article Sources ---")
        for ts in TRUSTED_SOURCES:
            slug = generate_slug(ts["name"])
            source = Source.query.filter_by(slug=slug).first()
            if not source:
                source = Source(
                    name=ts["name"],
                    slug=slug,
                    domain=ts["domain"],
                    authority_score=ts["score"],
                    is_active=True
                )
                db.session.add(source)
                print(f"Created trusted source: {ts['name']} ({slug})")
        db.session.commit()

        # Backfill Content rows
        print("\n--- Backfilling Content Source mappings ---")
        contents = Content.query.all()
        for c in contents:
            if c.object_type == "video":
                source = Source.query.filter_by(slug="youtube").first()
                if source:
                    c.source_id = source.id
                    c.ingestion_origin = "youtube"
            elif c.object_type == "post":
                source = Source.query.filter_by(slug="reddit").first()
                if source:
                    c.source_id = source.id
                    c.ingestion_origin = "reddit"
            elif c.object_type == "article":
                # Check primary article source via target relation
                target = db.session.get(Article, c.object_id)
                if target:
                    # Resolve primary source URL/name
                    if target.preferred_source_relation and target.preferred_source_relation.source:
                        c.source_id = target.preferred_source_relation.source.id
                    
                    # Set ingestion origin if none is set
                    if not c.ingestion_origin:
                        # Infer origin from content_source, default to gnews/newsapi/rss
                        # If content_source tells us 'api' or 'scraper' we can look at url/source name
                        origin = "newsapi"
                        if target.preferred_source_relation and "gnews" in (target.preferred_source_relation.url or ""):
                            origin = "gnews"
                        elif target.is_content_scraped:
                            origin = "rss"
                        c.ingestion_origin = origin

        db.session.commit()
        print("Content source mappings backfilled.")

        # Backfill Item rows
        print("\n--- Backfilling Item Source mappings ---")
        items = Item.query.all()
        for item in items:
            source_type = item.source_type or "aliexpress"
            slug = generate_slug(source_type)
            source = Source.query.filter_by(slug=slug).first()
            if not source:
                source = Source(
                    name=source_type.capitalize(),
                    slug=slug,
                    domain=f"{slug}.com",
                    is_active=True
                )
                db.session.add(source)
                db.session.flush()
                print(f"Created item source on-the-fly: {source.name} ({slug})")
            item.source_id = source.id

        db.session.commit()
        print("Item source mappings backfilled.")
        print("\n--- BACKFILL COMPLETE ---")

if __name__ == "__main__":
    backfill_providers()
