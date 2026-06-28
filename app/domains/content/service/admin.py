from sqlalchemy import select, or_, and_, func
from sqlalchemy.orm import joinedload, selectinload
from datetime import datetime, timezone, timedelta
from app.core.extensions import db
from app.domains.content.models import Content, Article, Video, Post
from app.domains.taxonomy.models import Category, Section, Source, Topic, Brand, IntentFacet, GenderFacet, PriceTierFacet
from app.domains.interaction.models import Comment, Reaction, View
from app.domains.relationships import ArticleSource

_CONTENT_SORT_MAP = {
    "id": Content.id,
    "published_at": Content.published_at,
    "ingested_at": Content.ingested_at,
    "view_count": Content.view_count,
    "like_count": Content.like_count,
    "comment_count": Content.comment_count,
    "share_count": Content.share_count,
    "save_count": Content.save_count,
    "score": Content.score,
    "title": Content.title,
}

def build_admin_contents_query(args, sort_by=None, sort_dir=None):
    sort_col = _CONTENT_SORT_MAP.get(sort_by, Content.published_at)
    sort_dir = sort_dir.lower() if sort_dir and sort_dir.lower() in ("asc", "desc") else "desc"

    search        = args.get("search")
    section_slug  = args.get("section")
    category_slug = args.get("category")
    object_type   = args.get("type")
    source        = args.get("source")
    status        = args.get("status")
    active        = args.get("active")
    published     = args.get("published")
    date_type     = args.get("date_type", "published_at")
    start_date    = args.get("start_date")
    end_date      = args.get("end_date")
    quality       = args.get("quality")

    query = db.session.query(Content).options(
        joinedload(Content.source),
        joinedload(Content.category),
        joinedload(Content.section),
    )

    if search and search.strip():
        term = f"%{search.strip()}%"
        if search.strip().isdigit():
            query = query.filter(or_(Content.id == int(search.strip()), Content.title.ilike(term)))
        else:
            query = query.filter(or_(Content.title.ilike(term), Content.preview_text.ilike(term)))
    if section_slug:
        query = query.join(Content.section).filter(Section.slug == section_slug)
    if category_slug:
        if category_slug == "uncategorized":
            query = query.filter(
                or_(Content.category_id.is_(None), Content.category.has(Category.slug == "uncategorized"))
            )
        else:
            query = query.join(Content.category).filter(Category.slug == category_slug)
    if object_type:
        query = query.filter(Content.object_type == object_type)
    if source:
        query = query.join(Content.source).filter(Source.slug == source)
    if status:
        query = query.filter(
            Content.object_type == "article",
            Content.object_id.in_(db.session.query(Article.id).filter(Article.status == status)),
        )
    if active:
        query = query.filter(Content.is_active == (active.lower() == "true"))
    if published:
        query = query.filter(Content.is_published == (published.lower() == "true"))

    topic_slug = args.get("topic")
    brand_slug = args.get("brand")
    origin     = args.get("ingestion_origin")
    intent_slug = args.get("intent")
    gender_slug = args.get("gender")
    price_tier_slug = args.get("price_tier")

    if topic_slug:
        if topic_slug == "none":
            query = query.filter(~Content.topics.any())
        else:
            query = query.filter(Content.topics.any(slug=topic_slug))
    if brand_slug:
        if brand_slug == "none":
            query = query.filter(~Content.brands.any())
        else:
            query = query.filter(Content.brands.any(slug=brand_slug))
    if origin:
        query = query.filter(Content.ingestion_origin == origin)
        
    if intent_slug:
        query = query.filter(Content.intent.has(slug=intent_slug))
    if gender_slug:
        query = query.filter(Content.gender.has(slug=gender_slug))
    if price_tier_slug:
        query = query.filter(Content.price_tier.has(slug=price_tier_slug))

    date_col = Content.published_at if date_type == "published_at" else Content.ingested_at
    if start_date:
        try:
            query = query.filter(date_col >= datetime.strptime(start_date, "%Y-%m-%d"))
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(date_col <= end_dt)
        except ValueError:
            pass

    if quality:
        if quality == "missing_category":
            query = query.filter(
                or_(Content.category_id.is_(None), Content.category.has(Category.slug == "uncategorized"))
            )
        elif quality == "missing_metadata":
            query = query.filter(
                or_(
                    Content.title.is_(None), Content.title == "",
                    Content.preview_text.is_(None), Content.preview_text == "",
                )
            )
        elif quality == "duplicate":
            dup_sub = (
                db.session.query(Content.title)
                .group_by(Content.title)
                .having(func.count(Content.id) > 1)
                .subquery()
            )
            query = query.filter(Content.title.in_(dup_sub))
        elif quality == "missing_topics":
            query = query.filter(~Content.topics.any())
        elif quality == "missing_brands":
            query = query.filter(~Content.brands.any())
        elif quality == "missing_source":
            query = query.filter(Content.source_id.is_(None))
        elif quality == "enrichment_failed":
            query = query.filter(
                Content.object_type == "article",
                Content.object_id.in_(db.session.query(Article.id).filter(Article.status == "failed"))
            )

    query = query.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())
    return query, quality

def load_admin_content_relations(page_items, quality):
    ids_by_type: dict[str, set] = {}
    for c in page_items:
        ids_by_type.setdefault(c.object_type, set()).add(c.object_id)

    targets_map = {}
    for obj_type, ids in ids_by_type.items():
        model = {"article": Article, "video": Video, "post": Post}.get(obj_type)
        if model:
            stmt = select(model).where(model.id.in_(list(ids)))
            if model == Article:
                stmt = stmt.options(selectinload(Article.article_sources).joinedload(ArticleSource.source))
            objs = db.session.execute(stmt).scalars().all()
            for obj in objs:
                targets_map[(obj_type, obj.id)] = obj

    duplicate_titles: set = set()
    if quality == "duplicate":
        titles = [c.title for c in page_items if c.title]
        if titles:
            dup_rows = db.session.execute(
                select(Content.title)
                .where(Content.title.in_(titles))
                .group_by(Content.title)
                .having(func.count(Content.id) > 1)
            ).scalars().all()
            duplicate_titles = set(dup_rows)
            
    return targets_map, duplicate_titles

def delete_admin_content_and_relations(content: Content) -> None:
    cid = content.id
    db.session.execute(
        Comment.__table__.delete().where(
            (Comment.target_type == "content") & (Comment.target_id == cid)
        )
    )
    db.session.execute(
        Reaction.__table__.delete().where(
            (Reaction.target_type == "content") & (Reaction.target_id == cid)
        )
    )
    db.session.execute(
        View.__table__.delete().where(
            (View.target_type == "content") & (View.target_id == cid)
        )
    )

    if content.object_type == "article":
        db.session.execute(Article.__table__.delete().where(Article.id == content.object_id))
    elif content.object_type == "video":
        db.session.execute(Video.__table__.delete().where(Video.id == content.object_id))
    elif content.object_type == "post":
        db.session.execute(Post.__table__.delete().where(Post.id == content.object_id))

    db.session.delete(content)

def get_admin_content_metadata():
    categories = db.session.execute(select(Category).order_by(Category.name)).scalars().all()
    sections   = db.session.execute(select(Section).order_by(Section.name)).scalars().all()
    sources    = db.session.execute(select(Source).order_by(Source.name)).scalars().all()
    topics     = db.session.execute(select(Topic).order_by(Topic.name)).scalars().all()
    brands     = db.session.execute(select(Brand).order_by(Brand.name)).scalars().all()
    intents    = db.session.execute(select(IntentFacet).order_by(IntentFacet.name)).scalars().all()
    genders    = db.session.execute(select(GenderFacet).order_by(GenderFacet.name)).scalars().all()
    price_tiers= db.session.execute(select(PriceTierFacet).order_by(PriceTierFacet.name)).scalars().all()
    origins = db.session.execute(select(Content.ingestion_origin).filter(Content.ingestion_origin.is_not(None)).distinct()).scalars().all()

    return {
        "categories": [{"id": c.id, "slug": c.slug, "name": c.name} for c in categories],
        "sections": [{"id": s.id, "slug": s.slug, "name": s.name} for s in sections],
        "sources": [{"slug": s.slug, "name": s.name} for s in sources],
        "topics": [{"slug": t.slug, "name": t.name} for t in topics],
        "brands": [{"slug": b.slug, "name": b.name} for b in brands],
        "intents": [{"slug": i.slug, "name": i.name} for i in intents],
        "genders": [{"slug": g.slug, "name": g.name} for g in genders],
        "price_tiers": [{"slug": p.slug, "name": p.name} for p in price_tiers],
        "origins": [{"slug": o, "name": o} for o in origins]
    }

def get_admin_content_stats():
    total = db.session.query(func.count(Content.id)).scalar()
    published = db.session.query(func.count(Content.id)).filter(Content.is_published == True).scalar()
    drafts = total - published
    failed = db.session.query(func.count(Article.id)).filter(Article.status == "failed").scalar()
    
    no_topics = db.session.query(func.count(Content.id)).filter(~Content.topics.any()).scalar()
    no_brands = db.session.query(func.count(Content.id)).filter(~Content.brands.any()).scalar()

    return {
        "total": total,
        "published": published,
        "drafts": drafts,
        "failed": failed,
        "no_topics": no_topics,
        "no_brands": no_brands
    }

def get_admin_content_dashboard_stats():
    type_counts = db.session.execute(select(Content.object_type, func.count(Content.id)).group_by(Content.object_type)).all()
    origin_counts = db.session.execute(select(Content.ingestion_origin, func.count(Content.id)).group_by(Content.ingestion_origin)).all()
    status_counts = db.session.execute(select(Article.status, func.count(Article.id)).group_by(Article.status)).all()
    
    total = db.session.query(func.count(Content.id)).scalar() or 0
    published = db.session.query(func.count(Content.id)).filter(Content.is_published == True).scalar() or 0
    failed = db.session.query(func.count(Article.id)).filter(Article.status == "failed").scalar() or 0
    scraped = db.session.query(func.count(Article.id)).filter(Article.is_content_scraped == True).scalar() or 0
    total_articles = db.session.query(func.count(Article.id)).scalar() or 1
    scrape_coverage = (scraped / total_articles) * 100
    
    no_tax = db.session.query(func.count(Content.id)).filter(~Content.topics.any(), ~Content.brands.any()).scalar() or 0

    origin_analytics = db.session.query(
        Content.ingestion_origin,
        func.count(Content.id).label("count"),
        func.avg(Article.quality_score).label("avg_quality"),
        func.avg(Article.word_count).label("avg_words"),
        func.avg(Content.view_count).label("avg_views")
    ).outerjoin(Article, Content.object_id == Article.id).group_by(Content.ingestion_origin).all()

    origin_table = []
    for row in origin_analytics:
        origin_table.append({
            "origin": row[0] or "Unknown",
            "count": row[1] or 0,
            "avg_quality": round(row[2], 1) if row[2] else 0,
            "avg_words": int(row[3]) if row[3] else 0,
            "avg_views": int(row[4]) if row[4] else 0
        })
        
    now = datetime.now(timezone.utc)
    d30 = now - timedelta(days=30)
    d90 = now - timedelta(days=90)
    
    freshness_counts = db.session.query(Content.published_at).filter(Content.published_at != None).all()
    freshness_dist = {"< 30 Days": 0, "30-90 Days": 0, "> 90 Days": 0}
    for (pub_at,) in freshness_counts:
        if pub_at.tzinfo is None:
            pub_at = pub_at.replace(tzinfo=timezone.utc)
        if pub_at > d30:
            freshness_dist["< 30 Days"] += 1
        elif pub_at > d90:
            freshness_dist["30-90 Days"] += 1
        else:
            freshness_dist["> 90 Days"] += 1
            
    authority_dist = {"High (67-100)": 0, "Medium (34-66)": 0, "Low (0-33)": 0}
    source_scores = db.session.query(Source.authority_score, func.count(Content.id)).join(Content, Content.source_id == Source.id).group_by(Source.authority_score).all()
    for score, count in source_scores:
        s = score or 0
        if s >= 67: authority_dist["High (67-100)"] += count
        elif s >= 34: authority_dist["Medium (34-66)"] += count
        else: authority_dist["Low (0-33)"] += count

    return {
        "kpi": {
            "total": total,
            "published": published,
            "drafts": total - published,
            "failed": failed,
            "no_tax": no_tax,
            "scrape_coverage": round(scrape_coverage, 1)
        },
        "type_dist": {row[0]: row[1] for row in type_counts},
        "origin_dist": {row[0] or 'Unknown': row[1] for row in origin_counts},
        "status_dist": {row[0] or 'Pending': row[1] for row in status_counts},
        "freshness_dist": freshness_dist,
        "authority_dist": authority_dist,
        "origin_table": origin_table
    }

def get_admin_pipeline_stats():
    origins = db.session.execute(select(Content.ingestion_origin).distinct()).scalars().all()
    stats_list = []
    
    for origin in origins:
        if not origin: continue
        
        counts = db.session.execute(
            select(Article.status, func.count(Article.id))
            .join(Content, Content.object_id == Article.id)
            .where(Content.object_type == "article")
            .where(Content.ingestion_origin == origin)
            .group_by(Article.status)
        ).all()
        
        status_map = {status: count for status, count in counts}
        total = sum(status_map.values())
        if total > 0:
            stats_list.append({
                "origin": origin,
                "pending": status_map.get("pending", 0),
                "enriching": status_map.get("enriching", 0),
                "failed": status_map.get("failed", 0),
                "complete": status_map.get("complete", 0),
                "total": total
            })
    return stats_list

def retry_admin_pipeline(origin):
    query = db.session.query(Article).join(Content, Content.object_id == Article.id).filter(
        Content.object_type == "article",
        Article.status == "failed"
    )
    if origin:
        query = query.filter(Content.ingestion_origin == origin)
        
    articles_to_retry = query.all()
    for a in articles_to_retry:
        a.status = "pending"
    return len(articles_to_retry)

def get_admin_deduplication_groups():
    dup_titles = db.session.execute(
        select(Content.title, func.count(Content.id))
        .group_by(Content.title)
        .having(func.count(Content.id) > 1)
        .order_by(func.count(Content.id).desc())
        .limit(20)
    ).all()
    
    groups = []
    for title, count in dup_titles:
        if not title: continue
        items = db.session.execute(select(Content).where(Content.title == title)).scalars().all()
        groups.append({
            "title": title,
            "count": count,
            "content_list": [{"id": i.id, "type": i.object_type, "published_at": i.published_at.isoformat() if i.published_at else None, "source": i.source.name if i.source else "None"} for i in items]
        })
    return groups

def get_admin_content_inspect_raw(id):
    content = db.session.scalar(
        select(Content).options(
            joinedload(Content.category),
            joinedload(Content.section),
            joinedload(Content.source),
            joinedload(Content.gender),
            joinedload(Content.intent),
            joinedload(Content.price_tier),
            selectinload(Content.brands),
            selectinload(Content.topics),
            selectinload(Content.linked_items),
            selectinload(Content.comments).joinedload(Comment.user)
        ).where(Content.id == id)
    )
    if not content:
        return None

    target = None
    if content.object_type in ("article", "video", "post"):
        model = {"article": Article, "video": Video, "post": Post}.get(content.object_type)
        if model:
            stmt = select(model).where(model.id == content.object_id)
            if model == Article:
                stmt = stmt.options(selectinload(Article.article_sources).joinedload(ArticleSource.source))
            target = db.session.scalar(stmt)
            
    return {"content": content, "target": target}


def build_content_inspect_data(content_id: int) -> dict | None:
    """
    Assemble the full inspect-view payload for a single content item.

    Delegates raw ORM fetching to get_admin_content_inspect_raw, then enriches
    the result with engagement scoring, taxonomy breadcrumbs, distribution history,
    and a structured inspect_table.  Returns None if the content is not found.
    """
    raw_data = get_admin_content_inspect_raw(content_id)
    if not raw_data:
        return None

    content = raw_data["content"]
    target  = raw_data["target"]

    sources: list[str] = []
    if content.object_type == "article" and target:
        sources = [s.source.name for s in target.sorted_source_relations if s.source]
    else:
        sources = [content.source.name] if content.source else []

    status_val = target.status if target and hasattr(target, "status") else "complete"

    # Lazy imports to avoid circular dependencies with route-layer helpers
    from app.web.routes.admin.helpers import format_datetime
    from app.web.routes.admin.tables import get_inspect_table
    from app.domains.interaction.service.scoring import get_content_engagement_score
    from app.domains.distribution.services import get_distribution_history

    engagement_score = get_content_engagement_score(content.id)

    sec_slug = content.section.slug  if content.section  else ""
    cat_slug = content.category.slug if content.category else ""
    sec_name = content.section.name  if content.section  else "Unassigned"
    cat_name = content.category.name if content.category else "Uncategorized"

    taxonomy_breadcrumb = [
        {"label": sec_name, "link": f"/admin/contents?section={sec_slug}"},
        {"label": cat_name, "link": f"/admin/contents?category={cat_slug}"},
    ]

    data = {
        "id":                 f"#{content.id}",
        "title":              content.title or "—",
        "type":               content.object_type,
        "taxonomy path":      {"value": taxonomy_breadcrumb, "is_breadcrumb": True},
        "engagement score":   str(engagement_score),
        "related brands":     ", ".join(b.name for b in content.brands)      if content.brands      else "—",
        "related topics":     ", ".join(t.name for t in content.topics)      if content.topics      else "—",
        "mentioned products": ", ".join(i.name for i in content.linked_items) if content.linked_items else "—",
        "attributes":         ", ".join(a.name for a in content.attributes)  if content.attributes  else "—",
        "available sources":  ", ".join(sources) if sources else "—",
        "primary source":     content.source.name if content.source else "—",
        "acquired via":       content.ingestion_origin or "—",
        "published at":       format_datetime(content.published_at) or "—",
        "ingested at":        format_datetime(content.ingested_at)  or "—",
        "enrichment status":  status_val,
        "status":             "Live Index" if content.is_published else "Draft",
        "renderation status": "Active"     if content.is_active    else "Inactive",
        "views":    "{:,}".format(content.view_count    or 0),
        "likes":    "{:,}".format(content.like_count    or 0),
        "dislikes": "{:,}".format(content.dislike_count or 0),
        "comments": "{:,}".format(content.comment_count or 0),
        "shares":   "{:,}".format(content.share_count   or 0),
        "saves":    "{:,}".format(content.save_count    or 0),
        "intent":      content.intent.name     if content.intent      else "—",
        "gender":      content.gender.name     if content.gender      else "—",
        "price tier":  content.price_tier.name if content.price_tier  else "—",
        "base score":  str(content.score        or 0),
        "review score": str(content.review_score or 0),
    }

    if content.object_type == "video" and target:
        data["platform"] = target.platform
        data["channel"]  = target.channel_name or "—"
    elif content.object_type == "post" and target:
        data["platform"]          = target.platform
        data["author"]            = target.author    or "—"
        data["subreddit"]         = target.subreddit or "—"
        data["platform upvotes"]  = str(target.upvotes        or 0)
        data["platform comments"] = str(target.comments_count or 0)
    elif content.object_type == "article" and target:
        data["is scraped"]               = "Yes" if target.is_content_scraped else "No"
        data["word count"]               = "{:,}".format(target.word_count or 0)
        data["read time"]                = f"{target.read_time_minutes} min" if hasattr(target, "read_time_minutes") else "—"
        data["article quality score"]    = str(target.quality_score or 0)
        data["last enrichment attempt"]  = (
            format_datetime(target.last_enrichment_attempt)
            if target.last_enrichment_attempt else "—"
        )

    inspect_table = get_inspect_table("contents", data)

    if target and hasattr(target, "url") and target.url:
        inspect_table["Related Metadata"].append({
            "label": "Source Link",
            "value": {"label": "View Original Link", "link": target.url, "external": True},
            "is_link": True,
        })

    article_sources_data = []
    if content.object_type == "article" and target and target.article_sources:
        article_sources_data = target.article_sources

    recent_comments = sorted(
        content.comments,
        key=lambda c: c.created_at or datetime.min,
        reverse=True
    )[:3]
    if recent_comments:
        inspect_table.setdefault("Related Metadata", [])
        for idx, c in enumerate(recent_comments):
            user_name = c.user.name if c.user else f"User #{c.user_id}"
            preview   = c.content[:100] + ("..." if len(c.content) > 100 else "")
            inspect_table["Related Metadata"].append({
                "label": f"Recent Comment {idx + 1}",
                "value": {"label": user_name, "detail": preview},
                "is_labeled": True,
            })

    distribution_history = get_distribution_history("content", content_id)

    return {
        "inspect_table":      inspect_table,
        "article_sources":    article_sources_data,
        "distribution_history": distribution_history,
        "inspect_id":         content.id,
        "content_title":      content.title or "",
    }

