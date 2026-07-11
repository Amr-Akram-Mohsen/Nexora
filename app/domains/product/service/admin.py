from sqlalchemy import select, func, or_
from sqlalchemy.orm import joinedload, selectinload
from datetime import datetime, timezone, timedelta
from app.core.extensions import db
from app.domains.product.models import Product, ProductVariant, ProductStoreLink, ProductImage, ProductSpecification
from app.domains.taxonomy.models import Category, Brand, Source
from app.domains.interaction.models import Comment

from app.domains.taxonomy.service.query import get_taxonomy_mappings

def get_admin_item_meta():
    categories = get_taxonomy_mappings(Category, used_in_model=Product, used_in_column=Product.category_id)
    brands = get_taxonomy_mappings(Brand, used_in_model=Product, used_in_column=Product.brand_id)
    sources = get_taxonomy_mappings(Source, used_in_model=Product, used_in_column=Product.source_id)

    product_types = db.session.execute(
        select(Product.product_type).distinct().order_by(Product.product_type)
    ).scalars().all()

    return {
        "categories": categories,
        "brands":     brands,
        "product_types": [t for t in product_types if t],
        "sources":    sources,
    }

def get_admin_item_health_stats():
    from sqlalchemy import case
    stats = db.session.execute(
        select(
            func.count(func.distinct(Product.id)).label("total_items"),
            func.count(func.distinct(case((Product.brand_id.isnot(None), Product.id), else_=None))).label("branded_items"),
            func.count(func.distinct(ProductImage.product_id)).label("items_with_images")
        )
        .select_from(Product)
        .outerjoin(ProductImage, ProductImage.product_id == Product.id)
    ).first()

    total_items = stats.total_items or 0
    branded_items = stats.branded_items or 0
    items_with_images = stats.items_with_images or 0

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    link_stats = db.session.execute(
        select(
            func.count(func.distinct(ProductVariant.product_id)).label("items_with_links"),
            func.count(func.distinct(case((ProductStoreLink.last_synced_at >= seven_days_ago, ProductVariant.product_id), else_=None))).label("recent_sync")
        )
        .select_from(ProductVariant)
        .join(ProductStoreLink, ProductStoreLink.variant_id == ProductVariant.id)
        .where(ProductStoreLink.is_active.is_(True))
    ).first()
    
    items_with_links = link_stats.items_with_links or 0
    items_with_recent_sync = link_stats.recent_sync or 0
    stale_sync_items = max(0, items_with_links - items_with_recent_sync)

    type_dist_rows = db.session.execute(
        select(Product.product_type, func.count(Product.id))
        .group_by(Product.product_type)
        .order_by(func.count(Product.id).desc())
    ).all()
    
    product_type_distribution = [
        {"type": r[0] or "Uncategorized", "count": r[1]}
        for r in type_dist_rows
    ]

    top_items_rows = db.session.execute(
        select(
            Product.id, 
            Product.name, 
            Product.click_count, 
            Product.view_count,
            Product.save_count,
            Product.like_count
        )
        .where(Product.view_count > 10)
        .order_by((Product.click_count * 1.0 / Product.view_count).desc())
        .limit(5)
    ).all()
    
    top_engagement_items = []
    for r in top_items_rows:
        ctr = round((r.click_count / r.view_count) * 100, 1) if r.view_count else 0
        save_rate = round((r.save_count / r.view_count) * 100, 1) if r.view_count else 0
        like_rate = round((r.like_count / r.view_count) * 100, 1) if r.view_count else 0
        top_engagement_items.append({
            "id": r.id,
            "name": r.name,
            "ctr": ctr,
            "save_rate": save_rate,
            "like_rate": like_rate
        })

    return {
        "total_items": total_items,
        "branded_items": branded_items,
        "items_with_images": items_with_images,
        "items_with_links": items_with_links,
        "stale_sync_items": stale_sync_items,
        "product_type_distribution": product_type_distribution,
        "top_engagement_items": top_engagement_items
    }

def load_admin_item_aggregates(page_ids):
    min_price_rows = db.session.execute(
        select(
            ProductVariant.product_id,
            func.min(ProductVariant.price).label("min_price"),
            func.max(ProductVariant.price).label("max_price"),
            ProductVariant.currency,
        )
        .where(ProductVariant.product_id.in_(page_ids), ProductVariant.price != None)
        .group_by(ProductVariant.product_id, ProductVariant.currency)
        .order_by(ProductVariant.product_id, func.min(ProductVariant.price))
    ).all()

    min_price_map: dict[int, dict] = {}
    for r in min_price_rows:
        if r.product_id not in min_price_map:
            min_price_map[r.product_id] = {
                "price": float(r.min_price), 
                "max_price": float(r.max_price) if r.max_price else None,
                "currency": r.currency
            }

    store_rows = db.session.execute(
        select(
            ProductVariant.product_id,
            func.count(ProductStoreLink.id).label("active_links"),
            func.max(ProductStoreLink.last_synced_at).label("last_synced_at"),
            func.max(ProductStoreLink.old_price).label("max_old_price")
        )
        .join(ProductStoreLink, ProductStoreLink.variant_id == ProductVariant.id)
        .where(
            ProductVariant.product_id.in_(page_ids),
            ProductStoreLink.is_active.is_(True),
        )
        .group_by(ProductVariant.product_id)
    ).all()

    store_info_map = {
        r.product_id: {
            "active_links": int(r.active_links),
            "last_synced_at": r.last_synced_at,
            "has_discount": r.max_old_price is not None and float(r.max_old_price) > 0
        }
        for r in store_rows
    }
    
    image_rows = db.session.execute(
        select(ProductImage.product_id, func.count(ProductImage.id).label("image_count"))
        .where(ProductImage.product_id.in_(page_ids))
        .group_by(ProductImage.product_id)
    ).all()
    image_info_map = {r.product_id: int(r.image_count) > 0 for r in image_rows}

    spec_rows = db.session.execute(
        select(ProductSpecification.product_id, func.count(ProductSpecification.id).label("spec_count"))
        .where(ProductSpecification.product_id.in_(page_ids))
        .group_by(ProductSpecification.product_id)
    ).all()
    spec_info_map = {r.product_id: int(r.spec_count) > 0 for r in spec_rows}

    return min_price_map, store_info_map, image_info_map, spec_info_map

def build_admin_items_query(args, sort_col, sort_dir):
    search        = args.get("search", "").strip()
    brand_slug    = args.get("brand")
    category_slug = args.get("category")
    source_slug   = args.get("source")
    has_images    = args.get("has_images")
    has_brand     = args.get("has_brand")
    availability  = args.get("availability")
    product_type     = args.get("product_type")

    stmt = select(Product).options(joinedload(Product.brand), joinedload(Product.category))

    if search:
        term = f"%{search}%"
        if search.isdigit():
            stmt = stmt.where(or_(Product.id == int(search), Product.name.ilike(term)))
        else:
            stmt = stmt.where(or_(Product.name.ilike(term), Product.description.ilike(term)))

    if brand_slug:
        stmt = stmt.join(Product.brand).where(Brand.slug == brand_slug)
    if category_slug:
        stmt = stmt.join(Product.category).where(Category.slug == category_slug)
    if source_slug:
        stmt = stmt.join(Product.source).where(Source.slug == source_slug)
    if product_type:
        stmt = stmt.where(Product.product_type == product_type)
        
    if has_images == "true":
        stmt = stmt.where(Product.images.any())
    elif has_images == "false":
        stmt = stmt.where(~Product.images.any())
        
    if has_brand == "true":
        stmt = stmt.where(Product.brand_id.isnot(None))
    elif has_brand == "false":
        stmt = stmt.where(Product.brand_id.is_(None))
        
    if availability and availability != "all":
        stmt = stmt.where(
            Product.variants.any(
                ProductVariant.store_links.any(
                    (ProductStoreLink.is_active == True) & (ProductStoreLink.availability == availability)
                )
            )
        )

    if sort_col == "min_price":
        price_sub = select(func.min(ProductVariant.price)).where(ProductVariant.product_id == Product.id).scalar_subquery()
        stmt = stmt.order_by(price_sub.asc() if sort_dir == "asc" else price_sub.desc())
    elif sort_col == "store_count":
        store_sub = select(func.count(ProductStoreLink.id)).join(ProductVariant, ProductVariant.id == ProductStoreLink.variant_id).where(ProductVariant.product_id == Product.id, ProductStoreLink.is_active == True).scalar_subquery()
        stmt = stmt.order_by(store_sub.asc() if sort_dir == "asc" else store_sub.desc())
    elif sort_col == "last_synced_at":
        sync_sub = select(func.max(ProductStoreLink.last_synced_at)).join(ProductVariant, ProductVariant.id == ProductStoreLink.variant_id).where(ProductVariant.product_id == Product.id).scalar_subquery()
        stmt = stmt.order_by(sync_sub.asc() if sort_dir == "asc" else sync_sub.desc())
    else:
        stmt = stmt.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())

    return stmt

def get_admin_items_page(args, sort_col, sort_dir, page, per_page):
    stmt = build_admin_items_query(args, sort_col, sort_dir)
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)

def get_admin_item(id):
    return db.session.get(Product, id)


def get_admin_item_inspect_raw(id):
    product = db.session.scalar(
        select(Product).options(
            joinedload(Product.category),
            joinedload(Product.brand),
            joinedload(Product.source),
            selectinload(Product.variants).selectinload(ProductVariant.store_links).joinedload(ProductStoreLink.store),
            selectinload(Product.linked_contents),
            selectinload(Product.images),
            selectinload(Product.specifications),
            selectinload(Product.comments).joinedload(Comment.user)
        ).where(Product.id == id)
    )
    return product

def get_admin_store_inspect_raw(id):
    from sqlalchemy import select, func, case
    from datetime import datetime, timezone, timedelta
    from app.domains.product.models import Store, ProductStoreLink, ProductVariant
    
    store = db.session.get(Store, id)
    if not store:
        return None
        
    product_count = db.session.scalar(
        select(func.count(func.distinct(ProductVariant.product_id)))
        .join(ProductStoreLink, ProductStoreLink.variant_id == ProductVariant.id)
        .where(ProductStoreLink.store_id == id)
    ) or 0
    
    now = datetime.now(timezone.utc)
    stale_date = now - timedelta(days=7)

    stats = db.session.execute(
        select(
            func.count(ProductStoreLink.id).label("total_links"),
            func.sum(case((ProductStoreLink.is_active == True, 1), else_=0)).label("active_links"),
            func.sum(case((ProductStoreLink.is_active == False, 1), else_=0)).label("inactive_links"),
            func.sum(case((ProductStoreLink.last_synced_at == None, 1), else_=0)).label("never_synced"),
            func.sum(case((ProductStoreLink.last_synced_at < stale_date, 1), else_=0)).label("stale_links"),
            func.sum(case((ProductStoreLink.availability == 'OutOfStock', 1), else_=0)).label("out_of_stock"),
            func.max(ProductStoreLink.last_synced_at).label("last_synced"),
            func.count(func.distinct(ProductStoreLink.program_name)).label("program_count"),
            func.avg(ProductStoreLink.commission_rate).label("avg_commission"),
            func.max(ProductStoreLink.commission_rate).label("max_commission"),
            func.sum(case((ProductStoreLink.commission_rate != None, 1), else_=0)).label("with_commission"),
            func.sum(case((ProductStoreLink.commission_rate == None, 1), else_=0)).label("without_commission"),
            func.sum(case((ProductStoreLink.tracking_code != None, 1), else_=0)).label("with_tracking"),
            func.min(ProductStoreLink.price).label("min_price"),
            func.avg(ProductStoreLink.price).label("avg_price"),
            func.max(ProductStoreLink.price).label("max_price"),
            func.sum(case(((ProductStoreLink.old_price != None) & (ProductStoreLink.old_price > ProductStoreLink.price), 1), else_=0)).label("with_discount"),
            func.avg(case(((ProductStoreLink.old_price != None) & (ProductStoreLink.old_price > ProductStoreLink.price), (ProductStoreLink.old_price - ProductStoreLink.price) / ProductStoreLink.old_price * 100), else_=None)).label("avg_discount_pct"),
            func.sum(case((ProductStoreLink.price == None, 1), else_=0)).label("null_price")
        )
        .where(ProductStoreLink.store_id == id)
    ).first()
    
    currency_mix_rows = db.session.execute(
        select(ProductStoreLink.currency, func.count(ProductStoreLink.id))
        .where(ProductStoreLink.store_id == id)
        .where(ProductStoreLink.currency != None)
        .group_by(ProductStoreLink.currency)
    ).all()
    currency_mix_list = [{"label": c[0], "detail": c[1]} for c in currency_mix_rows] if currency_mix_rows else []

    all_syncs = db.session.execute(
        select(ProductStoreLink.last_synced_at)
        .where(ProductStoreLink.store_id == id)
        .where(ProductStoreLink.last_synced_at != None)
    ).all()
    total_days = 0
    for (dt,) in all_syncs:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        total_days += (now - dt).days
    avg_sync_age = round(total_days / len(all_syncs), 1) if all_syncs else None

    return store, stats, product_count, currency_mix_list, avg_sync_age

