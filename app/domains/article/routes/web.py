from . import bp

from random import shuffle
from flask import request, render_template, Blueprint
from flask_login import current_user
from sqlalchemy import func
from app.core.extensions import db
from app.domains.system.models import Section
from app.domains.article.models import Article
from app.domains.item.models import Item, ItemVariant, ItemStoreLink
from ..service import get_related_articles, get_trending_articles
from app.domains.system.service import get_active_brands_for_section, get_active_topics_for_section, get_active_categories_for_section
from app.domains.interaction.service import record_view
from app.core.constants import TargetType
from app.shared.request import get_client_ip, get_country
from app.shared.parsing import safe_float

@bp.route("/sections/<section_slug>")
def sections(section_slug):
    from ..service import get_filtered_articles
    section = Section.query.filter(
        Section.slug == section_slug,
        Section.is_active == True
    ).first_or_404()

    active_filters = {
        'category': request.args.getlist('category'),
        'topic': request.args.getlist('topic'),
        'brand': request.args.getlist('brand'),
        'sort': request.args.get('sort', 'newest')
    }

    allowed_filters = set(section.allowed_filters or [])
    page = request.args.get('page', 1, type=int)

    pagination = get_filtered_articles(section, active_filters, allowed_filters, page=page)
    articles = pagination.items

    filter_options = {}
    if "category" in allowed_filters:
        filter_options["category"] = get_active_categories_for_section(section_slug)
    if "brand" in allowed_filters:
        filter_options["brand"] = get_active_brands_for_section(section_slug)
    if "topic" in allowed_filters:
        filter_options["topic"] = get_active_topics_for_section(section_slug)

    return render_template(
        "catalog-page.html",
        section=section,
        articles=articles,
        pagination=pagination,
        target_type="articles",
        allowed_filters=allowed_filters,
        filter_options=filter_options,
        active_filters=active_filters
    )



@bp.route("/articles/<int:article_id>")
def article_page(article_id):
    article = Article.query.options(
        db.selectinload(Article.linked_items)
            .selectinload(Item.variants)
            .selectinload(ItemVariant.store_links)
            .selectinload(ItemStoreLink.store),
        db.selectinload(Article.linked_items)
            .selectinload(Item.images)
    ).get_or_404(article_id)
    user = current_user if current_user.is_authenticated else None
    ip = None if user else get_client_ip()
    record_view(
        target=article,
        target_type=TargetType.ARTICLE,
        user=user,
        ip_address=ip
    )
    section_ids = [article.section_id]
    related_articles = get_related_articles(article)
    trending_articles = get_trending_articles(limit=6, days=7, section_ids=section_ids)
    
    return render_template(
        "article-page.html",
        article=article,
        related_articles=related_articles,
        trending_articles=trending_articles
    )


