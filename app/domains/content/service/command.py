from collections import defaultdict
from app.core.extensions import db
from ..models import Article, Content
from ...system.models import (
    Topic, Brand, AttributeFacet,
    GenderFacet, IntentFacet, PriceTierFacet, Source
)

from app.shared.utils.slug import generate_slug
from .content_access import resolve
from sqlalchemy import func, insert

def link_article_sources(session, article, data) -> bool:
    """Links an article to its specific source URL, ensuring uniqueness."""
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
    existing = session.query(ArticleSource).filter_by(
        url=url
    ).first()

    if existing:
        return False

    existing_relation = session.query(ArticleSource).filter_by(
        article_id=article.id,
        source_id=source.id
    ).first()

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

def delete_content(session, id: int) -> bool:
    content = session.get(Article, id)

    if not content:
        return False

    session.delete(content)
    # db.session.commit()  # Removed: Transaction control moved to Application layer
    return True

def create_content_entry(session, obj, object_type, published_at):
    """
    Creates a Content entry after the object is created.
    Prevents duplicates.
    """

    existing = session.query(Content).filter_by(
        object_type=object_type,
        object_id=obj.id
    ).first()

    if existing:
        return existing

    content = Content(
        object_type=object_type,
        object_id=obj.id,
        published_at=published_at
    )

    session.add(content)
    return content

def apply_relationships(session, content, data) -> dict:
    from collections import defaultdict
    updated_relationships = defaultdict(list)

    # -------- Topics --------
    for slug in data.get("topic_slugs", []):
        topic = Topic.get_by_slug(slug, session)
        if topic:
            if content.add_topic(topic):
                updated_relationships["topics"].append(topic.slug)

    # -------- Brands --------
    for slug in data.get("brand_slugs", []):
        brand = Brand.get_by_slug(slug, session)
        if brand:
            if content.add_brand(brand):
                updated_relationships["brands"].append(brand.slug)

    updated_relationships.setdefault("facets", {})

    # -------- Attributes --------
    for slug in data.get("facets", {}).get("attributes", []):
        attr = AttributeFacet.get_by_slug(slug, session)
        if attr:
            if content.add_attribute(attr):
                updated_relationships["facets"]["attributes"].append(attr.slug)

    # -------- Facets --------
    facets = data.get("facets", {})

    if facets.get("gender"):
        g = GenderFacet.get_by_slug(facets["gender"], session)
        if g and content.gender_id != g.id:
            content.gender_id = g.id
            updated_relationships["facets"]["gender"] = g.slug

    if facets.get("intent"):
        i = IntentFacet.get_by_slug(facets["intent"], session)
        if i and content.intent_id != i.id:
            content.intent_id = i.id
            updated_relationships["facets"]["intent"] = i.slug

    if facets.get("price_tier"):
        p = PriceTierFacet.get_by_slug(facets["price_tier"], session)
        if p and content.price_tier_id != p.id:
            content.price_tier_id = p.id
            updated_relationships["facets"]["price_tier"] = p.slug

    # -------- Sources (ONLY for article) --------
    if content.object_type == "article":
        obj = resolve(content, session)
        if obj:
            if link_article_sources(session, obj, data):
                updated_relationships["sources"] = [s.source.slug for s in obj.article_sources]
                updated_relationships["sources"].append(data.get("source_name").lower())
    
    return updated_relationships
