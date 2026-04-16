from random import shuffle
from flask import request, render_template, jsonify, redirect, url_for
from flask_login import current_user
from sqlalchemy import func

from app.models import db, Article, Section, Category, Topic, Brand, Item, ItemVariant, ItemStoreLink, Store
from app.services.item_service import get_search_items
from app.services.article_service import get_search_articles, get_active_brands_for_section, get_active_topics_for_section, get_related_articles, get_trending_articles
from app.services.interaction_service import record_view
from app.constants import TargetType
from app.utils.request import get_client_ip, get_country
from app.utils.parsing import safe_float
from . import bp

# ============== SEARCH LOGIC ================
@bp.route('/search', methods=['POST', 'GET'])
def search():
    if request.method == 'POST':
        q = (request.form.get('query') or '').strip()
    else:
        q = (request.args.get('query') or '').strip()

    items = get_search_items(q)
    articles = get_search_articles(q)    

    search_results = articles + items
    shuffle(search_results)

    # If AJAX request, return only the grid HTML
    
    return jsonify({
        'success': True,
        'html': render_template(
            'search-results.html',
            search_results=search_results,
            query=q,
            country=get_country()
        )
    })

@bp.route("/sections/<section_slug>")
def sections(section_slug):
    from app.services.article_service import get_filtered_articles
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

@bp.route("/items")
def items():
    from app.services.item_service import get_filtered_items
    page = request.args.get('page', 1, type=int)
    active_filters = {'sort': 'newest'}
    
    pagination = get_filtered_items(active_filters, page=page)
    items = pagination.items

    return render_template(
        "catalog-page.html",
        items=items,
        pagination=pagination,
        target_type="products",
        allowed_filters=["category", "brand", "type"],
        filter_options={
            "category": Category.query.join(Item).distinct().all(),
            "brand": Brand.query.join(Item).distinct().all(),
            "type": [t[0] for t in db.session.query(Item.item_type).distinct().all() if t[0]]
        },
        active_filters=active_filters
    )



@bp.route("/item/<int:item_id>/view_full_specs", methods=["POST"])
def view_full_specs(item_id):
    item = Item.query.get_or_404(item_id)
    html = render_template(
        "components/features/full-specs.html",
        full_specs=item.full_details
    )
    return jsonify({
        "html": html
    })

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
    section_ids = [s.id for s in article.sections]
    related_articles = get_related_articles(article)
    trending_articles = get_trending_articles(limit=6, days=7, section_ids=section_ids)
    
    return render_template(
        "article-page.html",
        article=article,
        related_articles=related_articles,
        trending_articles=trending_articles
    )

@bp.route("/deals")
def deals():
    from app.services.item_service import get_filtered_items
    active_filters = {
        'category': request.args.getlist('category'),
        'brand': request.args.getlist('brand'),
        'store': request.args.getlist('store'),
        'type': request.args.getlist('type'),
        'min_price': request.args.get('min_price'),
        'max_price': request.args.get('max_price'),
        'sort': request.args.get('sort', 'newest')
    }
    page = request.args.get('page', 1, type=int)

    pagination = get_filtered_items(active_filters, page=page)
    items = pagination.items

    filter_options = {
        "category": Category.query.join(Item).distinct().all(),
        "brand": Brand.query.join(Item).distinct().all(),
        "store": Store.query.join(ItemStoreLink).join(ItemVariant).join(Item).distinct().all(),
        "type": [t[0] for t in db.session.query(Item.item_type).distinct().all() if t[0]]
    }

    return render_template(
        "catalog-page.html",
        items=items,
        pagination=pagination,
        target_type="products",
        allowed_filters=["category", "brand", "store", "type"],
        filter_options=filter_options,
        active_filters=active_filters
    )



@bp.route("/items/<int:item_id>")
def item_page(item_id):
    item = Item.query.options(
        db.selectinload(Item.variants)
            .selectinload(ItemVariant.store_links)
            .selectinload(ItemStoreLink.store),
        db.selectinload(Item.images)
    ).get_or_404(item_id)

    user = current_user if current_user.is_authenticated else None
    ip = None if user else get_client_ip()
    record_view(
        item,
        TargetType.ITEM,
        user,
        ip)
    # analytics = get_item_analytics(item.id)
    # top_store = get_top_store_for_item(item.id)
    # print(f'\nAnalytics\n{analytics}')
    # print(f'\nTop Store\n{top_store}')
    return render_template(
        "item-page.html",
        item=item
    )

@bp.route('/compare')
def compare():
    """Side-by-side comparison of 2-4 products."""
    ids_str = request.args.get('ids', '')
    try:
        item_ids = [int(id_strip) for id_strip in ids_str.split(',') if id_strip.strip()]
    except ValueError:
        item_ids = []
    
    if not item_ids:
        # If no IDs, maybe show a "select items to compare" page or redirect
        return redirect(url_for('main.deals'))
        
    # Limit to 4 items for layout sanity
    item_ids = item_ids[:4]
    
    items = Item.query.options(
        db.joinedload(Item.brand),
        db.joinedload(Item.category),
        db.selectinload(Item.images),
        db.selectinload(Item.specifications),
        db.selectinload(Item.variants).selectinload(ItemVariant.store_links).selectinload(ItemStoreLink.store)
    ).filter(Item.id.in_(item_ids)).all()
    
    # Extract all possible specification categories from all items being compared
    all_categories = set()
    for item in items:
        all_categories.update(item.full_details.keys())
    
    return render_template(
        'compare-page.html',
        items=items,
        all_categories=sorted(list(all_categories))
    )
