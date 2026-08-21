from flask import current_app
from app.core.extensions import db
from app.infrastructure import cache
from app.infrastructure.cache import filters_from_normalized, normalize_filters
from app.domains.content.service import query as domain_query, get_content_by_id
from app.domains.recommendation.service.products import get_items_for_content as get_items_for_content_cached
from app.domains.interaction.service import record_view
from app.shared.constants.core import TargetType
from app.domains.taxonomy.service import get_section_by_slug, get_taxonomy_filters
from app.domains.serializers import serialize_model
from app.domains.taxonomy.models import Location, Source
from app.shared.utils.slug import generate_slug

@cache.memoize(timeout=600)
def get_contents_render_cached(filter_by_columns=('section',), filter_values=(None,), rows_count=None, exclude_ids=None):
    return domain_query.get_contents_render(filter_by_columns, filter_values, rows_count, exclude_ids)

@cache.memoize(timeout=3600)
def get_related_contents_cached(content_id, limit=6):
    return domain_query.get_related_contents(content_id, limit)

@cache.memoize(timeout=300)
def get_trending_contents_cached(limit=6, days=7, section_ids=None, exclude_ids=None):
    return domain_query.get_trending_contents(limit=limit, days=days, section_ids=section_ids, exclude_ids=exclude_ids)

def get_filtered_contents(section_id, active_filters, allowed_filters, page=1, per_page=24):
    return domain_query.get_filtered_contents(section_id, active_filters, allowed_filters, page, per_page)

@cache.memoize(timeout=300)
def get_filtered_contents_cached(section_id, active_filters_key, allowed_filters_key, page=1, per_page=24):
    return domain_query.get_filtered_contents(section_id, filters_from_normalized(active_filters_key), list(allowed_filters_key), page, per_page)

@cache.memoize(timeout=3600)
def get_carousel_contents_cached(active_filters_key, exclude_ids_key=None, limit=6):
    filters = filters_from_normalized(active_filters_key)
    res = domain_query.get_filtered_contents(None, filters, list(filters.keys()), page=1, per_page=limit, exclude_ids=exclude_ids_key)
    return res.get("products", [])

@cache.memoize(timeout=3600)
def get_globe_data_workflow():
    from sqlalchemy import func, select
    from app.domains.content.models import Content

    stmt = (
        select(Location, func.count(Content.id).label("content_count"))
        .join(Location.contents)
        .where(
            Location.latitude.is_not(None),
            Location.longitude.is_not(None),
            Content.is_active == True,
            Content.is_published == True
        )
        .group_by(Location.id)
        .having(func.count(Content.id) > 0)
    )
    results = db.session.execute(stmt).all()

    data = []
    for loc, count in results:
        data.append({
            "lat": loc.latitude,
            "lng": loc.longitude,
            "size": round(min(1.5, 0.1 + (count * 0.05)), 3),
            "title": loc.name,
            "slug": loc.slug,
            "content_count": count
        })
    return sorted(data, key=lambda x: x["size"], reverse=True)[:150]

@cache.memoize(timeout=1800)
def get_content_page_static_data(content_id):
    content = get_content_by_id(content_id)
    if content and content.get("linked_items"):
        from app.domains.product.serializers import serialize_item
        content["linked_items"] = [serialize_item(i) for i in content["linked_items"] if i]
    return content

def get_content_page_data(content_id):
    if not (content := get_content_page_static_data(content_id)): return None
    related = get_related_contents_cached(content["id"])
    seen_ids = {content["id"]} | {c["id"] for c in (related or []) if c.get("id")}
    trending = get_trending_contents_cached(limit=6, days=7, section_ids=[content["section_id"]] if content.get("section_id") else None, exclude_ids=tuple(seen_ids))
    linked_ids = {i["id"] for i in content.get("linked_items", []) if i.get("id")}
    matched = get_items_for_content_cached(content["id"], limit=6, exclude_ids=tuple(linked_ids) if linked_ids else None)
    
    tasks, results = {}, {}
    if (brands := content.get("brands")): tasks['entity'] = normalize_filters({"brand": [brands[0]["slug"]]})
    elif (topics := content.get("topics")): tasks['entity'] = normalize_filters({"topic": [topics[0]["slug"]]})
    
    source = content.get("source") or ({"name": content["target"]["source_name"], "slug": generate_slug(content["target"]["source_name"])} if content.get("target", {}).get("source_name") else None)
    if source and source.get("slug"): tasks['source'] = normalize_filters({"source": [source["slug"]]})
    
    if (authors := content.get("authors")) and len(authors) > 0 and (author_val := authors[0].get("name") if isinstance(authors[0], dict) else authors[0]):
        tasks['author'] = normalize_filters({"author": [author_val]})
        
    if (event := content.get("event")) and event.get("external_uri"): tasks['event'] = normalize_filters({"event": [event["external_uri"]]})
    
    if tasks:
        app = current_app._get_current_object()

        def _fetch(k, f):
            with app.app_context(): return k, get_carousel_contents_cached(f, exclude_ids_key=tuple([content["id"]]))
        with ThreadPoolExecutor(max_workers=4) as executor:
            for fut in as_completed({executor.submit(_fetch, k, v): k for k, v in tasks.items()}):
                try:
                    if (res := fut.result()[1]): results[fut.result()[0]] = res
                except Exception: pass

    return {
        "content": content, "related_contents": related, "trending_contents": trending, "matched_items": matched,
        "entity_carousel": {"title": f"More about {(brands or topics)[0]['name']}", "items": results['entity']} if results.get('entity') else None,
        "source_carousel": {"title": f"More from {source['name']}", "items": results['source']} if results.get('source') else None,
        "author_carousel": {"title": f"More by {author_val}", "items": results['author']} if results.get('author') else None,
        "event_carousel": {"title": "Developing Story", "items": results['event'], "event": event} if results.get('event') else None,
    }

def record_content_view(content_id, user, ip_address):
    record_view(target_id=content_id, target_type=TargetType.CONTENT, user=user, ip_address=ip_address)
    db.session.commit()

def get_feed_data(section_slug, active_filters, page=1):
    if section_slug == "all":

        class MockSection: id, name, slug, allowed_filters = None, "All Content", "all", ["category", "entity", "intent", "price_tier", "type", "attributes", "source", "event", "author", "location"]
        section = MockSection()
    elif not (section := get_section_by_slug(section_slug)): return None
    pagination = get_filtered_contents_cached(section.id, normalize_filters(active_filters), tuple(section.allowed_filters or []), page=page)
    cats = active_filters.get("category", [])
    filters = get_taxonomy_filters(section_slug, tuple(section.allowed_filters or []), tuple(sorted(cats)) if isinstance(cats, list) else (cats,))
    from app.application.recommendation.contextual import get_contextual_recommendations
    return {"section": serialize_model(section), "contents": pagination["products"], "pagination": pagination, "allowed_filters": section.allowed_filters, "filter_options": filters, "recommendations": get_contextual_recommendations(active_filters, len(pagination["products"]) > 0, section=section, target_type="content")}

def get_source_feed_data(source_slug, page=1):
    if not (source := db.session.query(Source).filter_by(slug=source_slug).first()): return None
    pagination = get_filtered_contents_cached(None, normalize_filters({"source": [source_slug]}), ("source",), page=page)
    return {
        "source": serialize_model(source),
        "section": {"name": source.name or "Source", "slug": "sources"},
        "contents": pagination["products"],
        "pagination": pagination,
        "allowed_filters": [],
        "filter_options": {},
        "recommendations": []
    }
