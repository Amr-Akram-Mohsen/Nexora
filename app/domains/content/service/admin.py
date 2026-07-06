from sqlalchemy import select, or_, and_, func
from sqlalchemy.orm import joinedload, selectinload
from datetime import datetime, timezone, timedelta
from app.core.extensions import db
from app.domains.content.models import Content, Article, Video, Post
from app.domains.taxonomy.models import Category, Section, Source, Topic, Brand, IntentFacet, GenderFacet, PriceTierFacet
from app.domains.interaction.models import Comment, Reaction, View
from app.domains.relationships import ArticleSource

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
    from app.domains.taxonomy.service.query import get_taxonomy_mappings
    
    categories = get_taxonomy_mappings(Category)
    sections   = get_taxonomy_mappings(Section)
    sources    = get_taxonomy_mappings(Source)
    topics     = get_taxonomy_mappings(Topic)
    brands     = get_taxonomy_mappings(Brand)
    intents    = get_taxonomy_mappings(IntentFacet)
    genders    = get_taxonomy_mappings(GenderFacet)
    price_tiers= get_taxonomy_mappings(PriceTierFacet)
    origins_rows = db.session.execute(select(Content.ingestion_origin).filter(Content.ingestion_origin.is_not(None)).distinct()).scalars().all()

    return {
        "categories": categories,
        "sections": sections,
        "sources": sources,
        "topics": topics,
        "brands": brands,
        "intents": intents,
        "genders": genders,
        "price_tiers": price_tiers,
        "origins": [{"slug": o, "name": o} for o in origins_rows]
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
