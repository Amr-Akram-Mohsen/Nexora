from random import shuffle
from flask import request, render_template, jsonify, redirect, url_for, Blueprint
from flask_login import current_user
from sqlalchemy import func
from app.core.extensions import db

from app.domains.core.models import Section, Category, Topic, Brand
from app.domains.article.models import Article
from app.domains.item.models import Item, ItemVariant, ItemStoreLink, Store
from .service import get_search_items
from app.domains.article.service import get_search_articles, get_active_brands_for_section, get_active_topics_for_section, get_related_articles, get_trending_articles
from app.domains.interaction.service import record_view
from app.core.constants import TargetType
from app.shared.request import get_client_ip, get_country
from app.shared.parsing import safe_float
bp = Blueprint('item', __name__)

@bp.route("/items")
def items():
    from .service import get_filtered_items
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

@bp.route("/deals")
def deals():
    from .service import get_filtered_items
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
        return redirect(url_for('item.deals'))
        
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
