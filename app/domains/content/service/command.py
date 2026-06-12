from collections import defaultdict
from app.core.extensions import db
from ..models import Article, Content
from ...taxonomy.models import (
    Topic, Brand, AttributeFacet,
    GenderFacet, IntentFacet, PriceTierFacet, Source
)

from app.shared.utils.slug import generate_slug
from .content_access import resolve
from sqlalchemy import func, insert, select

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

    # -------- Topics --------
    for slug in data.get("topic_slugs", []):
        topic = Topic.get_or_create(slug, session)
        if topic:
            if content.add_topic(topic):
                updated_relationships["topics"].append(topic.slug)

    # -------- Brands --------
    for slug in data.get("brand_slugs", []):
        brand = Brand.get_or_create(slug, session)
        if brand:
            if content.add_brand(brand):
                updated_relationships["brands"].append(brand.slug)

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

    # -------- Sources (ONLY for article) --------
    if content.object_type == "article":
        obj = resolve(content, session=session)
        if obj:
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
