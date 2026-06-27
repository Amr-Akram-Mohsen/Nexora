from sqlalchemy import select, or_, and_, func
from sqlalchemy.orm import joinedload, selectinload
from datetime import datetime, timezone, timedelta
from app.core.extensions import db
from app.domains.content.models import Content, Article, Video, Post
from app.domains.taxonomy.models import Category, Section, Source, Topic, Brand, IntentFacet, GenderFacet, PriceTierFacet
from app.domains.interaction.models import Comment, Reaction, View
from app.domains.relationships import ArticleSource
from app.web.routes.admin.helpers import parse_sort_params

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
    sort_col, sort_dir = parse_sort_params(sort_by, sort_dir, _CONTENT_SORT_MAP, Content.published_at)

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
