import logging
from slugify import slugify
from app.core.extensions import db
from app.domains.product.models import Product, ProductVariant, ProductImage, ProductStoreLink, Store, ProductSpecification
from app.domains.taxonomy.models import Brand, Category
logger = logging.getLogger(__name__)
DEFAULT_ITEM_TYPE = 'technology'
def get_or_create_brand(name: str) -> Brand:
    slug = slugify(name)
    brand = Brand.query.filter_by(slug=slug).first()
    if not brand:
        brand = Brand(name=name, slug=slug)
        db.session.add(brand)
        db.session.flush()
    return brand
def get_or_create_category(slug: str) -> Category:
    cat = Category.query.filter_by(slug=slug).first()
    if not cat:
        name = slug.replace('-', ' ').title()
        cat = Category(name=name, slug=slug)
        db.session.add(cat)
        db.session.flush()
    return cat
def get_amazon_store(country: str) -> Store:
    slug = f'amazon-{country.lower()}'
    store = Store.query.filter_by(slug=slug).first()
    if not store:
        store = Store(name=f'Amazon {country.upper()}', slug=slug, website=f'https://www.amazon.{('sa' if country.lower() == 'sa' else 'ae')}', country=country.upper(), currency='SAR' if country.lower() == 'sa' else 'AED', affiliate_network='Amazon Associates', logo_url='https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg', is_active=True)
        db.session.add(store)
        db.session.flush()
    return store
def store_amazon_item(data: dict) -> Product | None:
    brand_name = data.get('brand_name') or 'Unknown'
    brand = get_or_create_brand(brand_name)
    category_slug = data.get('category_slug') or 'technology'
    category = get_or_create_category(category_slug)
    store = get_amazon_store(data['country'])
    item_name = data['name']
    slug = slugify(item_name)
    product = Product.query.filter_by(slug=slug, brand_id=brand.id).first()
    if not product:
        product_type = DEFAULT_ITEM_TYPE
        if 'perfume' in category_slug or 'fragrance' in category_slug:
            product_type = 'perfumes'
        elif 'accessories' in category_slug or 'watch' in category_slug:
            product_type = 'accessories'
        product = Product(name=item_name, slug=slug, brand_id=brand.id, category_id=category.id, product_type=product_type, description='\n'.join(data.get('features', [])[:3]))
        db.session.add(product)
        db.session.flush()
        if data.get('image_url'):
            db.session.add(ProductImage(product_id=product.id, image_url=data['image_url'], position=0))
        variant = ProductVariant(product_id=product.id, title='Default', is_default=True, attributes={}, price=data.get('price'), old_price=data.get('old_price'), currency=data.get('currency'))
        db.session.add(variant)
        db.session.flush()
        if data.get('features'):
            db.session.add(ProductSpecification(product_id=product.id, category='features', spec_json={'bullets': data['features']}))
    else:
        variant = product.default_variant
        if not variant:
            variant = ProductVariant(product_id=product.id, title='Default', is_default=True, attributes={}, price=data.get('price'), old_price=data.get('old_price'), currency=data.get('currency'))
            db.session.add(variant)
            db.session.flush()
        elif variant.is_default:
            variant.price = data.get('price', variant.price)
            variant.old_price = data.get('old_price', variant.old_price)
            variant.currency = data.get('currency', variant.currency)
    link = ProductStoreLink.query.filter_by(variant_id=variant.id, store_id=store.id).first()
    from datetime import datetime
    if link:
        link.price = data.get('price', link.price)
        link.old_price = data.get('old_price')
        link.availability = data.get('availability', link.availability)
        link.affiliate_url = data['affiliate_url']
        link.last_checked_at = datetime.utcnow()
    else:
        link = ProductStoreLink(variant_id=variant.id, store_id=store.id, external_product_id=data['asin'], affiliate_url=data['affiliate_url'], price=data.get('price'), old_price=data.get('old_price'), currency=data['currency'], availability=data.get('availability', 'Unknown'), last_checked_at=datetime.utcnow(), is_active=True)
        db.session.add(link)
    try:
        db.session.commit()
        try:
            from app.infrastructure.cache.product import invalidate_item_after_write
            invalidate_item_after_write(product.id)
        except Exception:
            logger.warning('Product cache invalidation failed for product id=%s', product.id)
        return product
    except Exception:
        db.session.rollback()
        logger.exception(f'Error storing Amazon product {data['asin']}')
        return None
def run_ingestion_for_url(url: str, source_type: str='aliexpress', *, session=None, dry_run: bool=False) -> Product | None:
    logger.info('[IngestionWorkflow] Triggering ingestion for %s (source=%s)', url, source_type)
    return None