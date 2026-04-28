from . import bp

from flask import request, render_template
from flask_login import current_user
from app.core.extensions import db
from app.domains.system.models import Section
from app.domains.content.models import Content
from app.domains.item.models import Item, ItemVariant, ItemStoreLink
from ..service import get_related_contents, get_trending_contents
from ..content_access import resolve
from app.domains.system.service import get_active_brands_for_section, get_active_topics_for_section, get_active_categories_for_section
from app.domains.interaction.service import record_view
from app.shared.constants.core import TargetType
from app.shared.request import get_client_ip

@bp.route("/sections/<section_slug>")
def sections(section_slug):
    from ..service import get_filtered_contents
    section = Section.query.filter(
        Section.slug == section_slug,
        Section.is_active == True
    ).first_or_404()

    active_filters = {
        'category': [f for f in request.args.getlist('category') if f.strip()],
        'topic': [f for f in request.args.getlist('topic') if f.strip()],
        'brand': [f for f in request.args.getlist('brand') if f.strip()],
        'sort': request.args.get('sort', 'newest')
    }

    allowed_filters = set(section.allowed_filters or [])
    page = request.args.get('page', 1, type=int)

    pagination = get_filtered_contents(section, active_filters, allowed_filters, page=page)
    contents = pagination.items

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
        contents=contents,
        pagination=pagination,
        target_type="contents",
        allowed_filters=allowed_filters,
        filter_options=filter_options,
        active_filters=active_filters
    )

@bp.route("/contents/<int:content_id>")
def content_page(content_id):
    content = Content.query.options(
        db.selectinload(Content.linked_items)
            .selectinload(Item.variants)
            .selectinload(ItemVariant.store_links)
            .selectinload(ItemStoreLink.store),
        db.selectinload(Content.linked_items)
            .selectinload(Item.images)
    ).get_or_404(content_id)

    if content:
        content.target = resolve(content, db.session)

    user = current_user if current_user.is_authenticated else None
    ip = None if user else get_client_ip()
    record_view(
        target=content,
        target_type=TargetType.CONTENT,
        user=user,
        ip_address=ip
    )
    section_ids = [content.section_id]
    related_contents = get_related_contents(content)
    trending_contents = get_trending_contents(limit=6, days=7, section_ids=section_ids)
    
    return render_template(
        "content/dispatcher/page.html",
        content=content,
        related_contents=related_contents,
        trending_contents=trending_contents
    )


