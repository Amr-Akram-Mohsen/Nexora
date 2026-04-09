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
    section = Section.query.filter(
        Section.slug==section_slug,
        Section.is_active == True
    ).first_or_404()


    category = request.args.get("category_slug")
    topics = request.args.getlist("topic_slug")
    brands = request.args.getlist("brand_slug")

    allowed_filters = set(section.allowed_filters or [])

    query = (
        Article.query
        .join(Article.sections)
        .filter(Section.id == section.id)
    )
    
    if category:
        query = query.join(Article.category).filter(Category.slug == category)
    
    if topics and "topic" in allowed_filters:
        query = query.join(Article.topics).filter(Topic.slug.in_(topics))
    if brands and "brand" in allowed_filters:
        query = query.join(Article.brands).filter(Brand.slug.in_(brands))
    
    articles = (
        query
        .distinct()
        .order_by(Article.published_at.desc())
        .limit(50)
        .all()
    )

    filter_options = {}
    active_filters = {}

    if "category" in allowed_filters and category:
        # filter_options["category"] = get_active_categories_for_section(section_slug)
        active_filters['category'] = [category]
    if "brand" in allowed_filters:
        filter_options["brand"] = get_active_brands_for_section(section_slug)
        active_filters['brand'] = brands
    if "topic" in allowed_filters:
        filter_options["topic"] = get_active_topics_for_section(section_slug)
        active_filters['topic'] = topics
    return render_template(
        "sections-page.html",
        section=section,
        articles=articles,
        allowed_filters=allowed_filters,
        filter_options=filter_options,
        active_filters=active_filters
    )

@bp.route("/items")
def items():
    query = Item.query.options(
        db.joinedload(Item.brand),
        db.joinedload(Item.category),
        db.joinedload(Item.images)
    )

    # prods = filter_items_by_country(query).limit(20).all()
    prods = query.limit(20).all()

    return render_template('items-page.html',
                           category='Items',
                           items=prods)


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
    # 1. Base Query with Eager Loading
    query = Item.query.options(
        db.joinedload(Item.brand),
        db.joinedload(Item.category),
        db.selectinload(Item.images),
        db.selectinload(Item.variants).selectinload(ItemVariant.store_links).selectinload(ItemStoreLink.store)
    )

    # 2. Extract Filters from URL
    active_filters = {
        'category': request.args.getlist('category'),
        'brand': request.args.getlist('brand'),
        'store': request.args.getlist('store'),
        'type': request.args.getlist('type'),
        'min_price': request.args.get('min_price'),
        'max_price': request.args.get('max_price'),
        'sort': request.args.get('sort', 'newest')
    }

    # 3. Apply Filters
    if active_filters['category']:
        query = query.join(Item.category).filter(Category.slug.in_(active_filters['category']))
    if active_filters['brand']:
        query = query.join(Item.brand).filter(Brand.slug.in_(active_filters['brand']))
    if active_filters['type']:
        query = query.filter(Item.item_type.in_(active_filters['type']))
    
    # Store filtering requires a join through variants and store_links
    if active_filters['store']:
        query = query.join(Item.variants).join(ItemVariant.store_links).join(ItemStoreLink.store).filter(Store.slug.in_(active_filters['store']))

    # Price filtering
    if active_filters['min_price'] or active_filters['max_price']:
        query = query.join(Item.variants)
        if active_filters['min_price']:
            query = query.filter(ItemVariant.price >= float(active_filters['min_price']))
        if active_filters['max_price']:
            query = query.filter(ItemVariant.price <= float(active_filters['max_price']))

    # 4. Sorting
    if active_filters['sort'] == 'price_low':
        query = query.join(Item.variants).filter(ItemVariant.is_default == True).order_by(ItemVariant.price.asc())
    elif active_filters['sort'] == 'price_high':
        query = query.join(Item.variants).filter(ItemVariant.is_default == True).order_by(ItemVariant.price.desc())
    elif active_filters['sort'] == 'popular':
        query = query.order_by(Item.view_count.desc())
    else: # newest
        query = query.order_by(Item.created_at.desc())

    # 5. Fetch Filter Options for Sidebar
    # We want only active categories/brands that have items
    categories = Category.query.join(Item).distinct().all()
    brands = Brand.query.join(Item).distinct().all()
    stores = Store.query.join(ItemStoreLink).join(ItemVariant).join(Item).distinct().all()
    types = db.session.query(Item.item_type).distinct().all()
    types = [t[0] for t in types if t[0]]

    items = query.distinct().limit(40).all()

    return render_template(
        "deals-page.html",
        items=items,
        categories=categories,
        brands=brands,
        stores=stores,
        types=types,
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
