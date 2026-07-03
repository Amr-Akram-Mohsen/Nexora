from app.domains.taxonomy.models import Category, Brand, Topic, Section


def serialize_taxonomy(t, counts=None, health=None):
    data = {
        "id": t.id,
        "name": t.name,
        "is_active": getattr(t, 'is_active', False),
    }
    if isinstance(t, Category):
        data["hierarchy level"] = "Leaf" if t.is_leaf else "Parent"
    if isinstance(t, Section):
        data['description'] = t.description
        data['is_configured'] = bool(t.allowed_filters)
    if isinstance(t, Brand):
        data['industry'] = t.industry or "—"
    if isinstance(t, (Brand, Topic)):
        data['is_featured'] = getattr(t, 'is_featured', False)
        
    if counts:
        for k, v in counts.items():
            data[k] = v
            
    if health:
        data["health"] = health
        
    return data


def serialize_category(c):
    return {
        "id": c.id,
        "name": c.name,
        "slug": c.slug,
        "is_active": c.is_active,
        "is_leaf": c.is_leaf,
        "sort_order": c.sort_order,
        "parent_id": c.parent_id,
    }


def serialize_brand(b):
    return {
        "id": b.id,
        "name": b.name,
        "slug": b.slug,
        "industry": b.industry,
        "is_active": b.is_active,
        "is_featured": b.is_featured,
        "sort_order": b.sort_order,
    }


def serialize_topic(t):
    return {
        "id": t.id,
        "name": t.name,
        "slug": t.slug,
        "is_active": t.is_active,
        "is_featured": t.is_featured,
        "sort_order": t.sort_order,
    }


def serialize_section(s):
    return {
        "id": s.id,
        "name": s.name,
        "slug": s.slug,
        "description": s.description,
        "is_active": s.is_active,
        "sort_order": s.sort_order,
    }


def serialize_attribute(a):
    return {
        "id": a.id,
        "name": a.name,
        "slug": a.slug,
        "category_id": a.category_id,
        "category_name": a.category.name if a.category else "Global",
    }


def serialize_source_inspect_dto(raw_tuple):
    if not raw_tuple:
        return None

    (
        source, content_count, analytics, type_counts, channel_counts,
        category_counts, status_counts, eng_stats, fetch_health,
        primary_count, secondary_count, top_articles
    ) = raw_tuple

    avg_quality = round(analytics[0], 1) if analytics and analytics[0] else 0
    avg_words = int(analytics[1]) if analytics and analytics[1] else 0
    scraped_count = analytics[2] if analytics and analytics[2] else 0
    scrape_cov = round((scraped_count / content_count * 100), 1) if content_count > 0 else 0
    date_min = analytics[3].isoformat() if analytics and analytics[3] else None
    date_max = analytics[4].isoformat() if analytics and analytics[4] else None

    type_breakdown = {r[0]: r[1] for r in type_counts}
    channels = [r[0] for r in channel_counts]
    pipeline_status = {r[0]: r[1] for r in status_counts}

    top_articles_data = [{"id": r[0], "title": r[1] or "Untitled", "views": r[2]} for r in top_articles]

    return {
        "id": source.id,
        "name": source.name,
        "slug": source.slug,
        "domain": source.domain,
        "is_active": source.is_active,
        "authority_score": source.authority_score,
        "logo_url": source.logo_url,
        
        "avg_quality_score": avg_quality,
        "avg_word_count": avg_words,
        "scrape_coverage": scrape_cov,
        "date_min": date_min,
        "date_max": date_max,
        
        "channels": channels,
        "last_fetch": fetch_health.last_fetch.isoformat() if fetch_health and fetch_health.last_fetch else None,
        "success_count": fetch_health.success or 0 if fetch_health else 0,
        "failure_count": fetch_health.failures or 0 if fetch_health else 0,
        "consecutive_failures": fetch_health.consecutive or 0 if fetch_health else 0,
        
        "article_count": type_breakdown.get('article', 0),
        "video_count": type_breakdown.get('video', 0),
        "post_count": type_breakdown.get('post', 0),
        "categories_covered": category_counts,
        
        "pipeline_pending": pipeline_status.get('pending', 0),
        "pipeline_enriching": pipeline_status.get('enriching', 0),
        "pipeline_complete": pipeline_status.get('complete', 0),
        "pipeline_failed": pipeline_status.get('failed', 0),
        
        "total_views": eng_stats.views or 0 if eng_stats else 0,
        "total_likes": eng_stats.likes or 0 if eng_stats else 0,
        "total_saves": eng_stats.saves or 0 if eng_stats else 0,
        "total_comments": eng_stats.comments or 0 if eng_stats else 0,
        
        "primary_attribution_count": primary_count,
        "secondary_attribution_count": secondary_count,
        
        "top_articles": top_articles_data
    }
