from sqlalchemy import select, func, or_, case, cast, Date
from app.core.extensions import db
from app.domains.taxonomy.models import Category, Brand, Topic, Section, AttributeFacet, Source
from app.shared.utils.slug import generate_slug
from app.domains.content.models import Content, Article
from app.domains.item.models import Item
from app.domains.external.models import LastAPIFetch, APIUsage
from app.domains.relationships import content_brands, content_topics, content_attributes, ArticleSource

def get_admin_sources_page(page, per_page, search):
    stmt = select(Source)
    if search:
        term = f"%{search}%"
        stmt = stmt.where(or_(
            Source.name.ilike(term),
            Source.slug.ilike(term),
            Source.domain.ilike(term),
            Source.id.in_(
                select(Content.source_id)
                .where(Content.ingestion_origin.ilike(term))
            )
        ))
    stmt = stmt.order_by(Source.authority_score.desc(), Source.name.asc())
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    page_source_ids = [s.id for s in pagination.items]

    if page_source_ids:
        content_agg = db.session.execute(
            select(
                Content.source_id,
                func.count(Content.id).label("content_count"),
                func.max(Content.ingested_at).label("latest_ingested_at"),
                func.sum(
                    Content.view_count + Content.like_count + Content.dislike_count
                    + Content.save_count + Content.comment_count
                ).label("engagement")
            )
            .where(Content.source_id.in_(page_source_ids))
            .group_by(Content.source_id)
        ).all()
        content_agg_map = {r.source_id: r for r in content_agg}

        channels_rows = db.session.execute(
            select(Content.source_id, Content.ingestion_origin)
            .where(Content.source_id.in_(page_source_ids))
            .where(Content.ingestion_origin.is_not(None))
            .distinct()
        ).all()
        channels_map = {}
        for r in channels_rows:
            channels_map.setdefault(r.source_id, []).append(r.ingestion_origin)
    else:
        content_agg_map, channels_map = {}, {}

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    serialized = []
    for s in pagination.items:
        agg             = content_agg_map.get(s.id)
        content_count   = agg.content_count if agg else 0
        latest_activity = agg.latest_ingested_at.isoformat() if agg and agg.latest_ingested_at else None
        engagement      = int(agg.engagement) if agg and agg.engagement is not None else 0
        
        freshness_days = None
        if agg and agg.latest_ingested_at:
            latest = agg.latest_ingested_at
            if latest.tzinfo is None:
                latest = latest.replace(tzinfo=timezone.utc)
            freshness_days = (now - latest).days

        if not s.is_active:
            status_val = "failed"
        elif content_count == 0 or (freshness_days is not None and freshness_days > 7):
            status_val = "warning"
        else:
            status_val = "healthy"
            
        tier = 1 if s.authority_score >= 80 else (2 if s.authority_score >= 50 else 3)
        channels = channels_map.get(s.id, [])
        
        serialized.append({
            "id":              s.id,
            "logo-url":        s.logo_url,
            "link":            {'url': f'https://{s.domain}', 'name': s.name},
            "tier":            tier,
            "channels":        channels,
            "freshness":       freshness_days,
            "content-count":   content_count,
            "engagement":      engagement,
            "status":          status_val,
            "slug":            s.slug,
        })
    return pagination, serialized

def get_admin_source_health_stats():
    from datetime import datetime, timezone, timedelta
    
    now = datetime.now(timezone.utc)
    
    sources = db.session.execute(select(Source.id, Source.slug, Source.is_active)).all()
    
    content_agg = db.session.execute(
        select(Content.source_id, func.count(Content.id), func.max(Content.ingested_at))
        .group_by(Content.source_id)
    ).all()
    content_map = {r[0]: {"count": r[1], "latest": r[2]} for r in content_agg}
    
    healthy = 0
    warning = 0
    failed = 0
    silent = 0
    
    for s_id, s_slug, is_active in sources:
        if not is_active:
            failed += 1
            continue
            
        c_stats = content_map.get(s_id, {"count": 0, "latest": None})
        c_count = c_stats["count"]
        latest = c_stats["latest"]
        
        is_silent = False
        if latest:
            if latest.tzinfo is None:
                latest = latest.replace(tzinfo=timezone.utc)
            if (now - latest) > timedelta(days=7):
                silent += 1
                is_silent = True
                
        if c_count == 0 or is_silent:
            warning += 1
        else:
            healthy += 1
            
    return {
        "total": len(sources),
        "active": len(sources) - failed,
        "healthy": healthy,
        "warning": warning,
        "failed": failed,
        "silent": silent
    }

def build_admin_source_inspect_data(id):
    source = db.session.get(Source, id)
    if not source:
        return None
        
    content_count = db.session.scalar(select(func.count(Content.id)).filter(Content.source_id == id)) or 0
    

    analytics = db.session.query(
        func.avg(Article.quality_score),
        func.avg(Article.word_count),
        func.count(Article.id).filter(Article.is_content_scraped == True),
        func.min(Content.published_at),
        func.max(Content.published_at)
    ).select_from(Content).join(Article, Content.object_id == Article.id).filter(Content.source_id == id, Content.object_type == 'article').first()
    
    avg_quality = round(analytics[0], 1) if analytics and analytics[0] else 0
    avg_words = int(analytics[1]) if analytics and analytics[1] else 0
    scraped_count = analytics[2] if analytics and analytics[2] else 0
    scrape_cov = round((scraped_count / content_count * 100), 1) if content_count > 0 else 0
    date_min = analytics[3].strftime('%Y-%m-%d') if analytics and analytics[3] else "—"
    date_max = analytics[4].strftime('%Y-%m-%d') if analytics and analytics[4] else "—"
    
    type_counts = db.session.execute(
        select(Content.object_type, func.count(Content.id))
        .where(Content.source_id == id)
        .group_by(Content.object_type)
    ).all()
    type_breakdown = {r[0]: r[1] for r in type_counts}
    
    channel_counts = db.session.execute(
        select(Content.ingestion_origin, func.count(Content.id))
        .where(Content.source_id == id)
        .where(Content.ingestion_origin.is_not(None))
        .group_by(Content.ingestion_origin)
    ).all()
    channels = [r[0] for r in channel_counts]
    
    category_counts = db.session.scalar(
        select(func.count(func.distinct(Content.category_id)))
        .where(Content.source_id == id)
    ) or 0
    
    status_counts = db.session.execute(
        select(Article.status, func.count(Article.id))
        .join(Content, Content.object_id == Article.id)
        .where(Content.source_id == id)
        .where(Content.object_type == 'article')
        .group_by(Article.status)
    ).all()
    pipeline_status = {r[0]: r[1] for r in status_counts}
    
    eng_stats = db.session.execute(
        select(
            func.sum(Content.view_count).label("views"),
            func.sum(Content.like_count).label("likes"),
            func.sum(Content.save_count).label("saves"),
            func.sum(Content.comment_count).label("comments")
        ).where(Content.source_id == id)
    ).first()
    
    fetch_health = db.session.execute(
        select(
            func.sum(LastAPIFetch.success_count).label("success"),
            func.sum(LastAPIFetch.failure_count).label("failures"),
            func.max(LastAPIFetch.consecutive_failures).label("consecutive"),
            func.max(LastAPIFetch.last_fetched_at).label("last_fetch")
        )
        .where(func.lower(LastAPIFetch.source) == source.slug.lower())
    ).first()
    
    primary_count = db.session.scalar(
        select(func.count(Article.id))
        .where(Article.primary_source_id != None)
        .join(ArticleSource, Article.primary_source_id == ArticleSource.id)
        .where(ArticleSource.source_id == id)
    ) or 0
    secondary_count = db.session.scalar(
        select(func.count(ArticleSource.id))
        .where(ArticleSource.source_id == id)
    ) or 0
    secondary_count = max(0, secondary_count - primary_count)
    
    top_articles = db.session.execute(
        select(Content.id, Content.title, Content.view_count)
        .where(Content.source_id == id)
        .where(Content.object_type == 'article')
        .order_by(Content.view_count.desc())
        .limit(5)
    ).all()
    top_articles_data = [{"id": r[0], "title": r[1] or "Untitled", "views": r[2]} for r in top_articles]
    
    data = {
        "id": f"#{source.id}",
        "name": source.name,
        "slug": source.slug,
        "domain": source.domain,
        "status": "active" if source.is_active else "inactive",
        "authority score": str(source.authority_score),
        "avg quality score": str(avg_quality),
        "avg word count": str(avg_words),
        "scrape coverage": f"{scrape_cov}%",
        "published date range": f"{date_min} to {date_max}",
        
        "channels": ", ".join(channels) if channels else "None",
        "last fetch": fetch_health.last_fetch.strftime('%Y-%m-%d %H:%M') if fetch_health and fetch_health.last_fetch else "—",
        "success count": str(fetch_health.success or 0),
        "failure count": str(fetch_health.failures or 0),
        "consecutive failures": str(fetch_health.consecutive or 0),
        
        "article count": str(type_breakdown.get('article', 0)),
        "video count": str(type_breakdown.get('video', 0)),
        "post count": str(type_breakdown.get('post', 0)),
        "categories covered": str(category_counts),
        
        "pending": str(pipeline_status.get('pending', 0)),
        "enriching": str(pipeline_status.get('enriching', 0)),
        "complete": str(pipeline_status.get('complete', 0)),
        "failed": str(pipeline_status.get('failed', 0)),
        
        "total views": str(eng_stats.views or 0) if eng_stats else "0",
        "total likes": str(eng_stats.likes or 0) if eng_stats else "0",
        "total saves": str(eng_stats.saves or 0) if eng_stats else "0",
        "total comments": str(eng_stats.comments or 0) if eng_stats else "0",
        
        "primary attribution count": str(primary_count),
        "secondary attribution count": str(secondary_count)
    }
    return {
        "raw_data": data,
        "inspect_id": source.id,
        "source_header": {
            "name": source.name,
            "domain": source.domain,
            "logo_url": source.logo_url
        },
        "top_articles": top_articles_data
    }

def get_admin_sources_quality_data():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    rows = db.session.execute(
        select(
            Source.name,
            func.avg(Article.quality_score).label("avg_quality"),
            func.count(Article.id).label("total_articles"),
            func.sum(cast(Article.is_content_scraped, db.Integer)).label("scraped_articles"),
            func.avg(Article.word_count).label("avg_words"),
            func.max(Content.ingested_at).label("latest_ingested")
        )
        .join(Content, Content.source_id == Source.id)
        .join(Article, Article.id == Content.object_id)
        .where(Content.object_type == 'article')
        .group_by(Source.name)
    ).all()

    quality_leaderboard = []
    scrape_leaderboard = []
    word_counts = []
    freshness_index = []

    for name, avg_q, total_art, scraped_art, avg_w, latest_ingest in rows:
        q_score = round(avg_q, 1) if avg_q else 0
        if q_score >= 70:
            tier = "High"
        elif q_score >= 40:
            tier = "Medium"
        else:
            tier = "Low"
        quality_leaderboard.append({"source": name, "avg_quality": q_score, "tier": tier})

        total = total_art or 0
        scraped = scraped_art or 0
        scrape_pct = round((scraped / total * 100), 1) if total > 0 else 0
        if scrape_pct >= 90:
            health = "Healthy"
        elif scrape_pct >= 50:
            health = "Warning"
        else:
            health = "Critical"
        scrape_leaderboard.append({"source": name, "scrape_pct": scrape_pct, "health": health})

        words = int(avg_w) if avg_w else 0
        word_counts.append({"source": name, "avg_words": words})

        if latest_ingest:
            latest = latest_ingest
            if latest.tzinfo is None:
                latest = latest.replace(tzinfo=timezone.utc)
            days_stale = (now - latest).days
            if days_stale > 30:
                severity = "Critical"
            elif days_stale > 7:
                severity = "Warning"
            else:
                severity = "Healthy"
            freshness_index.append({
                "source": name,
                "latest_ingested": latest.strftime('%Y-%m-%d %H:%M'),
                "days_stale": days_stale,
                "severity": severity
            })

    quality_leaderboard.sort(key=lambda x: x["avg_quality"], reverse=True)
    scrape_leaderboard.sort(key=lambda x: x["scrape_pct"], reverse=True)
    word_counts.sort(key=lambda x: x["avg_words"], reverse=True)
    freshness_index.sort(key=lambda x: x["days_stale"], reverse=True)

    word_count_data = {
        "labels": [w["source"] for w in word_counts[:15]],
        "data": [w["avg_words"] for w in word_counts[:15]]
    }

    yield_data = {"labels": [], "datasets": []}
    
    usage_rows = db.session.execute(
        select(APIUsage.api_name, APIUsage.date, func.sum(APIUsage.request_count))
        .group_by(APIUsage.api_name, APIUsage.date)
        .order_by(APIUsage.date)
    ).all()
    
    content_rows = db.session.execute(
        select(Content.ingestion_origin, cast(Content.ingested_at, Date), func.count(Content.id))
        .group_by(Content.ingestion_origin, cast(Content.ingested_at, Date))
        .order_by(cast(Content.ingested_at, Date))
    ).all()

    usage_map = {}
    for api_name, date_val, req_count in usage_rows:
        if api_name not in usage_map:
            usage_map[api_name] = {}
        usage_map[api_name][str(date_val)] = req_count

    content_map = {}
    for origin, date_val, count in content_rows:
        if not origin: continue
        if origin not in content_map:
            content_map[origin] = {}
        content_map[origin][str(date_val)] = count

    all_dates = set()
    for o, dates in usage_map.items():
        all_dates.update(dates.keys())
    for o, dates in content_map.items():
        all_dates.update(dates.keys())
    all_dates = sorted(list(all_dates))[-14:]

    channels = set(usage_map.keys()) | set(content_map.keys())
    
    for channel in channels:
        ds_data = []
        for d in all_dates:
            reqs = usage_map.get(channel, {}).get(d, 0)
            arts = content_map.get(channel, {}).get(d, 0)
            if reqs > 0:
                ds_data.append(round(arts / reqs, 2))
            elif arts > 0:
                ds_data.append(arts)
            else:
                ds_data.append(0)
        yield_data["datasets"].append({
            "label": channel,
            "data": ds_data
        })
    yield_data["labels"] = all_dates

    return quality_leaderboard, scrape_leaderboard, freshness_index, word_count_data, yield_data
