from app.domains.content.service import get_content_by_id
from app.application.content.query_service import (
    get_related_contents_cached,
    get_trending_contents_cached,
    get_carousel_contents_cached,
)
from app.application.recommendation.query_service import get_items_for_content_cached
from app.domains.interaction.service import record_view
from app.infrastructure import cache
from app.infrastructure.cache import normalize_filters
from app.shared.constants.core import TargetType
from app.infrastructure import cache
from app.shared.constants.core import TargetType


@cache.memoize(timeout=1800)
def get_content_page_static_data(content_id):
    return get_content_by_id(content_id)


def get_content_page_data(content_id):
    """
    Orchestrates data for a single content/article page.

    Returns:
        content          — serialized content dict
        related_contents — scored related content products
        trending_contents— trending content in the same section
        matched_items    — products matched by the Article↔Product matcher (affil. CTA)
    """
    content = get_content_page_static_data(content_id)
    # content is now a serialized dictionary
    if not content:
        return None

    related_contents = get_related_contents_cached(content["id"])
    
    seen_content_ids = {content["id"]}
    if related_contents:
        seen_content_ids.update(c["id"] for c in related_contents if c.get("id"))

    # section is a serialized dict as well
    section_ids = [content["section_id"]] if content.get("section_id") else None
    trending_contents = get_trending_contents_cached(
        limit=6, days=7, section_ids=section_ids, exclude_ids=tuple(seen_content_ids)
    )

    # Items matched via the Content↔Product matcher — primary affiliate signal
    # Exclude any directly linked products from matched products
    linked_product_ids = {i["id"] for i in content.get("linked_items", []) if i.get("id")}
    matched_items = get_items_for_content_cached(content["id"], limit=6, exclude_ids=tuple(linked_product_ids) if linked_product_ids else None)

    # ── Personalization Carousels ──
    entity_carousel = None
    author_carousel = None
    source_carousel = None
    
    exclude_ids = tuple([content["id"]])

    # 1. Entity Carousel (More About [Entity])
    top_entity = None
    if content.get("brands"):
        top_entity = content["brands"][0]
        entity_type = "brand"
    elif content.get("topics"):
        top_entity = content["topics"][0]
        entity_type = "topic"
        
    if top_entity:
        items = get_carousel_contents_cached(
            normalize_filters({entity_type: [top_entity["slug"]]}), 
            exclude_ids_key=exclude_ids
        )
        if items:
            entity_carousel = {
                "title": f"More about {top_entity['name']}",
                "items": items
            }

    # 2. Source Carousel (More from [Source])
    if content.get("source"):
        source = content["source"]
        items = get_carousel_contents_cached(
            normalize_filters({"source": [source["slug"]]}),
            exclude_ids_key=exclude_ids
        )
        if items:
            source_carousel = {
                "title": f"More from {source['name']}",
                "items": items
            }

    # 3. Author Carousel (More by [Author])
    authors = content.get("authors")
    if authors:
        # Check if it's a list of dicts (authors relation) or just string/list of strings
        if isinstance(authors, list) and len(authors) > 0:
            author_val = authors[0].get("name") if isinstance(authors[0], dict) else authors[0]
            if author_val:
                items = get_carousel_contents_cached(
                    normalize_filters({"author": [author_val]}),
                    exclude_ids_key=exclude_ids
                )
                if items:
                    author_carousel = {
                        "title": f"More by {author_val}",
                        "items": items
                    }

    return {
        "content": content,
        "related_contents": related_contents,
        "trending_contents": trending_contents,
        "matched_items": matched_items,
        "entity_carousel": entity_carousel,
        "author_carousel": author_carousel,
        "source_carousel": source_carousel,
    }


def record_content_view(content_id, user, ip_address):
    """
    Records an article/content view interaction.
    """
    record_view(
        target_id=content_id,
        target_type=TargetType.CONTENT,
        user=user,
        ip_address=ip_address,
    )
    from app.core.extensions import db
    db.session.commit()
