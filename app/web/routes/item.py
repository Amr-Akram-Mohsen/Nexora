from flask import Blueprint, request, render_template, jsonify, redirect, url_for, abort
from flask_login import current_user
from app.application.item.get_catalog import get_catalog_data
from app.application.item.get_item_page import get_item_page_data
from app.application.item.compare_items import get_comparison_data
from app.domains.item.service import get_item_by_id
from app.shared.request import get_client_ip
from app.domains.interaction.service import record_view
from app.shared.constants.core import TargetType

bp = Blueprint("item", __name__)

@bp.route("/item/<int:item_id>/view_full_specs", methods=["POST"])
def view_full_specs(item_id):
    # This is a small helper, but still should use service
    item = get_item_by_id(item_id)
    if not item:
        abort(404)
        
    html = render_template(
        "commercial/features/full-details.html",
        full_specs=item.full_details
    )
    return jsonify({
        "html": html
    })

@bp.route("/deals")
def deals():
    active_filters = {
        'category': [f for f in request.args.getlist('category') if f.strip()],
        'brand': [f for f in request.args.getlist('brand') if f.strip()],
        'store': [f for f in request.args.getlist('store') if f.strip()],
        'type': [f for f in request.args.getlist('type') if f.strip()],
        'min_price': request.args.get('min_price'),
        'max_price': request.args.get('max_price'),
        'sort': request.args.get('sort', 'newest')
    }
    page = request.args.get('page', 1, type=int)

    data = get_catalog_data(active_filters, page=page)

    return render_template(
        "commercial/catalog/catalog-page.html",
        target_type="items",
        allowed_filters=["category", "brand", "store", "type"],
        active_filters=active_filters,
        **data
    )

@bp.route("/items/<int:item_id>")
def item_page(item_id):
    from app.application.item.get_item_page import record_item_view
    from app.core.extensions import db
    
    user = current_user if current_user.is_authenticated else None
    ip_address = None if user else get_client_ip()
    
    data = get_item_page_data(item_id)
    if not data:
        abort(404)

    # Orchestrate Query + Command
    record_item_view(item_id, user, ip_address)
    db.session.commit()
    
    return render_template(
        "commercial/page/item.html",
        **data
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
        return redirect(url_for('item.deals'))
        
    data = get_comparison_data(item_ids)
    if not data:
        return redirect(url_for('item.deals'))
    
    return render_template(
        'commercial/catalog/compare-page.html',
        **data
    )
