from ...models import Content
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from app.shared.constants.core import TargetType
from app.core.extensions import db
from app.domains.taxonomy.models import Section, Category, Brand, IntentFacet, Entity
from app.domains.interaction.models import View
from app.domains.relationships import ContentEntity
from .utils import build_content_stmt, build_ranked_content_stmt, fetch_serialized_contents
from app.infrastructure import cache

def get_trending_contents(
limit=6, days=7, section_ids=None, object_type=None, exclude_ids=None, session=None):
    session = session or db.session
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Use a simplified fast query for trending to avoid 30s timeouts on cold boot
    stmt = build_content_stmt(active_only=True, published_only=True, eager_load='list')
    stmt = stmt.where(Content.published_at >= cutoff)
    
    if exclude_ids:
        stmt = stmt.where(Content.id.notin_(list(exclude_ids)))
    if object_type:
        stmt = stmt.where(Content.object_type == object_type)
    if section_ids:
        stmt = stmt.join(Content.section).where(Section.id.in_(section_ids))
        
    # Sort by the pre-aggregated view_count instead of live calculating exponential decay on the View table
    stmt = stmt.order_by(Content.view_count.desc(), Content.published_at.desc())
    
    if limit:
        stmt = stmt.limit(limit)
    return fetch_serialized_contents(stmt, session)

@cache.memoize(timeout=300)
def get_popular_contents(section_id: int | None=None, category_slugs: tuple | None=None, brand_slugs: tuple | None=None, intent_slugs: tuple | None=None, limit: int=6, session=None) -> list[dict]:
    session = session or db.session
    stmt = build_content_stmt(active_only=True, published_only=True, eager_load='list')
    if section_id:
        stmt = stmt.where(Content.section_id == section_id)
    if category_slugs:
        stmt = stmt.join(Content.category).where(Category.slug.in_(list(category_slugs)))
    if brand_slugs:
        stmt = stmt.join(Content.content_entities).join(ContentEntity.entity).where(Entity.entity_type == 'brand', Entity.slug.in_(list(brand_slugs)))
    if intent_slugs:
        stmt = stmt.join(Content.intent).where(IntentFacet.slug.in_(list(intent_slugs)))
    stmt = stmt.order_by(Content.view_count.desc(), Content.published_at.desc())
    if limit:
        stmt = stmt.limit(limit)
    return fetch_serialized_contents(stmt, session)