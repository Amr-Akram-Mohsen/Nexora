from app.domains.product.service import get_filtered_items, get_distinct_product_types, get_distinct_stores, get_item_by_id, get_related_items, serialize_item, get_items_by_ids
from app.domains.taxonomy.service import get_distinct_item_categories, get_distinct_item_brands
from app.infrastructure.cache import filters_from_normalized, normalize_filters, cache
from app.domains.product.serializers import serialize_item_detail
from app.domains.interaction.service import record_view
from app.shared.constants.core import TargetType
from app.domains.recommendation.service.products import get_contents_for_item as get_contents_for_item_cached
from app.application.recommendation.contextual import get_contextual_recommendations
from app.core.extensions import db
def get_catalog_data(active_filters, page=1):
    canonical_filters = filters_from_normalized(normalize_filters(active_filters))
    pagination = get_filtered_items(canonical_filters, page=page)
    filter_options = {'category': get_distinct_item_categories(), 'brand': get_distinct_item_brands(), 'store': get_distinct_stores(), 'type': get_distinct_product_types()}
    has_results = len(pagination.get('products', [])) > 0
    recommendation_blocks = get_contextual_recommendations(active_filters, has_results, target_type='commercial')
    return {'products': pagination.get('products', []), 'pagination': pagination, 'filter_options': filter_options, 'recommendations': recommendation_blocks}
@cache.memoize(timeout=1800)
def get_item_page_data(product_id):
    raw_item = get_item_by_id(product_id, serialize=False, load='detail')
    if not raw_item:
        return None
    product = serialize_item_detail(raw_item)
    related = get_related_items(raw_item)
    related_contents = get_contents_for_item_cached(product_id, limit=12)
    related_articles = []
    related_videos = []
    buying_guides = []
    for c in related_contents:
        section_slug = c.get('section', {}).get('slug') if c.get('section') else None
        if c.get('object_type') == 'video':
            related_videos.append(c)
        elif c.get('object_type') == 'article' and section_slug == 'guides':
            buying_guides.append(c)
        elif c.get('object_type') == 'article':
            related_articles.append(c)
    return {'product': product, 'variant_data': product.get('variant_data', []), 'related_items': [serialize_item(i) for i in related], 'related_contents': related_contents, 'related_articles': related_articles, 'related_videos': related_videos, 'buying_guides': buying_guides}
def record_item_view(product_id, user, ip_address):
    record_view(target_id=product_id, target_type=TargetType.PRODUCT, user=user, ip_address=ip_address)
    db.session.commit()
def get_item_spec_groups_workflow(product_id):
    from app.domains.product.service import get_item_spec_groups
    return get_item_spec_groups(product_id)
def get_comparison_data(product_ids):
    if not product_ids:
        return None
    product_ids = product_ids[:4]
    products = get_items_by_ids(product_ids, serialize=True)
    if not products:
        return None
    all_categories = set()
    for product in products:
        full_details = product.get('full_details')
        if full_details:
            all_categories.update(full_details.keys())
    return {'products': products, 'all_categories': sorted(list(all_categories))}