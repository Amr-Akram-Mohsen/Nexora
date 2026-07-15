from collections import defaultdict
from app.core.extensions import db
from ..models import Article, Content, Event
from ...taxonomy.models import (
    AttributeFacet,
    GenderFacet, IntentFacet, PriceTierFacet, Source, Category, Entity
)
from app.domains.relationships import ContentEntity

from app.shared.utils.slug import generate_slug
from .content_access import resolve
from sqlalchemy import func, insert, select

def sync_content_fields(content, obj, object_type: str) -> None:
    """
    Centralised sync: keeps Content wrapper fields in sync with the child model.
    Call this whenever Article/Video/Post changes publication-relevant state.
    """
    content.title = obj.title
    content.preview_text = getattr(obj, "preview_text", None)
    content.score = getattr(obj, "quality_score", 0.0)
    if object_type == "article":
        content.is_published = (obj.status == "published")

def link_article_sources(article, data, session=None) -> bool:
    """Links an article to its specific source URL, ensuring uniqueness."""
    if session is None:
        session = db.session

    changed = False
    source_name = data.get("source_name")
    url = data.get("url")

    published_at = data.get("published_at")
    if not source_name or not url:
        return False

    slug = generate_slug(source_name)
    source = Source.get_by_slug(slug, session)

    if not source:
        # 🔹 Dynamic Source Creation with Tiered Authority
        from urllib.parse import urlparse
        from app.shared.constants.taxonomy import TRUSTED_SOURCES
        
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
            
        source = session.query(Source).filter_by(domain=domain).first()
        
        if not source:
            # Default score
            authority_score = 50
            
            # Check for trusted domain match
            for s_trusted in TRUSTED_SOURCES:
                t_domain = s_trusted["domain"].lower()
                if domain == t_domain or domain.endswith("." + t_domain):
                    authority_score = s_trusted.get("score", 70)
                    break
            
            source = Source(
                name=source_name,
                slug=slug,
                domain=domain,
                authority_score=authority_score,
                is_active=True
            )
            session.add(source)
            session.flush() # Ensure ID is available

    from ...relationships import ArticleSource
    
    # 🔹 Check if this specific URL is already in the system (unique constraint)
    stmt_url = select(ArticleSource).where(ArticleSource.url == url)
    existing = session.execute(stmt_url).scalars().first()

    if existing:
        return False

    stmt_relation = select(ArticleSource).where(
        ArticleSource.article_id == article.id,
        ArticleSource.source_id == source.id
    )
    existing_relation = session.execute(stmt_relation).scalars().first()

    if existing_relation:
        return False

    relation = ArticleSource(
        article_id=article.id,
        source_id=source.id,
        url=url,
        published_at=published_at
    )

    session.add(relation)
    session.flush() # Get relation.id

    # 🔹 Update Article's Primary Source (Performance Optimization)
    article.update_primary_source()
    return True


def apply_relationships(content, data, session=None) -> dict:
    if session is None:
        session = db.session

    updated_relationships = defaultdict(list)


    # -------- Attributes --------
    facets_data = data.get("facets", {})
    if facets_data.get("attributes"):
        updated_relationships.setdefault("facets", {})
        updated_relationships["facets"].setdefault("attributes", [])
        
        for slug in facets_data["attributes"]:
            attr = AttributeFacet.get_or_create(slug, session)
            if attr:
                if content.add_attribute(attr):
                    updated_relationships["facets"]["attributes"].append(attr.slug)

    # -------- Facets --------
    if facets_data.get("gender") or facets_data.get("intent") or facets_data.get("price_tier"):
        updated_relationships.setdefault("facets", {})

    if facets_data.get("gender"):
        g = GenderFacet.get_by_slug(facets_data["gender"], session)
        if g and content.gender_id != g.id:
            content.gender_id = g.id
            updated_relationships["facets"]["gender"] = g.slug

    if facets_data.get("intent"):
        i = IntentFacet.get_or_create(facets_data["intent"], session)
        if i and content.intent_id != i.id:
            content.intent_id = i.id
            updated_relationships["facets"]["intent"] = i.slug

    if facets_data.get("price_tier"):
        p = PriceTierFacet.get_or_create(facets_data["price_tier"], session)
        if p and content.price_tier_id != p.id:
            content.price_tier_id = p.id
            updated_relationships["facets"]["price_tier"] = p.slug

    # -------- Entities, Events, and Article Categories (NewsAPI AI) --------
    obj = resolve(content, session=session)
    if obj:
        if content.object_type == "article":
            # Events
            if data.get("er_event_data") or data.get("er_event_uri"):
                event_data = data.get("er_event_data") or {}
                event_uri = event_data.get("uri") or data.get("er_event_uri")
                if event_uri:
                    title_raw = event_data.get("title")
                    title_str = title_raw.get("eng", str(title_raw)) if isinstance(title_raw, dict) else (title_raw or data.get("title"))
                    
                    sum_raw = event_data.get("summary")
                    summary_str = sum_raw.get("eng", str(sum_raw)) if isinstance(sum_raw, dict) else sum_raw
                    
                    from datetime import datetime
                    event_date_str = event_data.get("eventDate")
                    event_date = datetime.fromisoformat(event_date_str.replace("Z", "+00:00")) if event_date_str else None
                    
                    event = Event.get_or_create(
                        external_uri=event_uri, 
                        session=session, 
                        title=title_str,
                        summary=summary_str,
                        event_date=event_date,
                        article_count=event_data.get("articleCount", 0),
                        importance=event_data.get("importance"),
                        image_url=event_data.get("image"),
                        event_type=event_data.get("type")
                    )
                    if event and (obj.event_id is None or obj.event_id != event.id):
                        obj.event_id = event.id
                        updated_relationships["event"] = event.external_uri

            # Categories (Article Categories)
            if data.get("er_categories"):
                for cat_data in data["er_categories"]:
                    cat_label = cat_data if isinstance(cat_data, str) else cat_data.get("name", cat_data.get("label", ""))
                    if not cat_label: continue
                    cat = Category.get_or_create(cat_label, session=session)
                    if cat and cat not in obj.categories:
                        obj.categories.append(cat)
                        updated_relationships.setdefault("categories", []).append(cat.slug)

        # Entities (Concepts) - Applies to ALL content types
        if data.get("er_concepts"):
            for concept in data["er_concepts"]:
                if isinstance(concept, str):
                    concept_uri = None
                    concept_label = concept
                    entity_type = "tag"
                    score = 0
                else:
                    concept_uri = concept.get("uri")
                    concept_label = concept.get("label", {}).get("eng", concept.get("label", "")) if isinstance(concept.get("label"), dict) else concept.get("label", "")
                    entity_type = concept.get("type", "tag")
                    score = concept.get("score", 0)

                    if not concept_label: continue

                    entity = Entity.get_or_create(
                        name=concept_label, 
                        session=session, 
                        external_uri=concept_uri, 
                        entity_type=entity_type,
                        provider="event_registry",
                        image_url=concept.get("image")
                    )
                    
                    if entity:
                        origin = "diffbot" if data.get("ingestion_method") == "diffbot" else "event_registry"
                        ce = ContentEntity.get_or_create(
                            content_id=content.id,
                            entity_id=entity.id,
                            session=session,
                            origin=origin,
                            relevance_score=score,
                            confidence=score / 100.0 if score > 1 else score,
                        )
                        updated_relationships.setdefault("entities", []).append(entity.slug)
                    # If this is a location, also populate the Locations model!
                    if entity_type in ("location", "place", "loc"):
                        from app.domains.taxonomy.models import Location
                        country_label = concept.get("location", {}).get("country", {}).get("label", {}).get("eng")
                        loc = Location.get_or_create(concept_label, session=session, country_name=country_label)
                        if loc and loc not in content.locations:
                            content.locations.append(loc)
                            updated_relationships.setdefault("locations", []).append(loc.slug)

    # -------- Sources (ONLY for article) --------
    if content.object_type == "article":
        obj = resolve(content, session=session)
        if obj:
            if not data.get("source_name") and "siteName" in extended_metadata:
                data["source_name"] = extended_metadata["siteName"]
            if not data.get("url"):
                data["url"] = obj.url
                
            link_article_sources(obj, data, session=session)
            if obj.preferred_source_relation and obj.preferred_source_relation.source:
                content.source_id = obj.preferred_source_relation.source.id
                updated_relationships["sources"] = [s.source.slug for s in obj.article_sources]
                if data.get("source_name"):
                    updated_relationships["sources"].append(data.get("source_name").lower())
    
    # For video and post, get-or-create their platform source
    elif content.object_type in ("video", "post"):
        platform_name = data.get("platform") or content.object_type
        slug = generate_slug(platform_name)
        source = Source.get_by_slug(slug, session)
        if not source:
            domain = f"{slug}.com"
            source = Source(
                name=platform_name.capitalize(),
                slug=slug,
                domain=domain,
                authority_score=100, # maximum authority for first-party/direct platforms
                is_active=True
            )
            session.add(source)
            session.flush()
        content.source_id = source.id
        updated_relationships["sources"] = [slug]

    return updated_relationships

def delete_content_and_relations(content: Content, session=None) -> None:
    from app.domains.interaction.models import Comment, Reaction, View
    if session is None:
        session = db.session
    cid = content.id
    session.execute(
        Comment.__table__.delete().where(
            (Comment.target_type == "content") & (Comment.target_id == cid)
        )
    )
    session.execute(
        Reaction.__table__.delete().where(
            (Reaction.target_type == "content") & (Reaction.target_id == cid)
        )
    )
    session.execute(
        View.__table__.delete().where(
            (View.target_type == "content") & (View.target_id == cid)
        )
    )

    if content.object_type == "article":
        session.execute(Article.__table__.delete().where(Article.id == content.object_id))
    elif content.object_type == "video":
        session.execute(Video.__table__.delete().where(Video.id == content.object_id))
    elif content.object_type == "post":
        session.execute(Post.__table__.delete().where(Post.id == content.object_id))

    session.delete(content)

def execute_bulk_content_actions(action, contents, category_id=None, session=None):
    if session is None:
        session = db.session
    if action == "activate":
        for c in contents:
            c.is_active = True
    elif action == "deactivate":
        for c in contents:
            c.is_active = False
    elif action == "publish":
        for c in contents:
            c.is_published = True
    elif action == "unpublish":
        for c in contents:
            c.is_published = False
    elif action == "review":
        for c in contents:
            c.is_published = False
    elif action == "recategorize":
        from ...taxonomy.models import Category
        if category_id is None:
            raise ValueError("Category ID is required for recategorize action")
        category = session.get(Category, int(category_id))
        if not category:
            raise ValueError("Target category not found")
        for c in contents:
            c.category_id = category.id
    elif action == "delete":
        for c in contents:
            delete_content_and_relations(c, session)
    else:
        raise ValueError("Unsupported bulk action")
