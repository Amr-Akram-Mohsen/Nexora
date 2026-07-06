from sqlalchemy import select, func, or_
from sqlalchemy.orm import joinedload, selectinload
from datetime import datetime, timezone, timedelta
from app.core.extensions import db
from app.domains.item.models import Item, ItemVariant, ItemStoreLink, ItemImage, ItemSpecification
from app.domains.taxonomy.models import Category, Brand, Source
from app.domains.interaction.models import Comment

def get_admin_item_meta():
    categories = db.session.execute(
        select(Category.id, Category.name, Category.slug)
        .where(Category.id.in_(select(Item.category_id).distinct()))
        .order_by(Category.name)
    ).mappings().all()

    brands = db.session.execute(
        select(Brand.id, Brand.name, Brand.slug)
        .where(Brand.id.in_(select(Item.brand_id).distinct()))
        .order_by(Brand.name)
    ).mappings().all()

    item_types = db.session.execute(
        select(Item.item_type).distinct().order_by(Item.item_type)
    ).scalars().all()

    sources = db.session.execute(
        select(Source.id, Source.name, Source.slug)
        .where(Source.id.in_(select(Item.source_id).distinct()))
        .order_by(Source.name)
    ).mappings().all()

    return {
        "categories": [dict(r) for r in categories],
        "brands":     [dict(r) for r in brands],
        "item_types": [t for t in item_types if t],
        "sources":    [dict(r) for r in sources],
    }

def get_admin_item_health_stats():
    total_items = db.session.scalar(select(func.count(Item.id))) or 0
    branded_items = db.session.scalar(select(func.count(Item.id)).where(Item.brand_id.isnot(None))) or 0
    
    items_with_images = db.session.scalar(
        select(func.count(func.distinct(ItemImage.item_id)))
    ) or 0
    
    items_with_links = db.session.scalar(
        select(func.count(func.distinct(ItemVariant.item_id)))
        .join(ItemStoreLink, ItemStoreLink.variant_id == ItemVariant.id)
        .where(ItemStoreLink.is_active.is_(True))
    ) or 0
    
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    items_with_recent_sync = db.session.scalar(
        select(func.count(func.distinct(ItemVariant.item_id)))
        .join(ItemStoreLink, ItemStoreLink.variant_id == ItemVariant.id)
        .where(ItemStoreLink.is_active.is_(True), ItemStoreLink.last_synced_at >= seven_days_ago)
    ) or 0
    stale_sync_items = max(0, items_with_links - items_with_recent_sync)

    type_dist_rows = db.session.execute(
        select(Item.item_type, func.count(Item.id))
        .group_by(Item.item_type)
        .order_by(func.count(Item.id).desc())
    ).all()
    
    item_type_distribution = [
        {"type": r[0] or "Uncategorized", "count": r[1]}
        for r in type_dist_rows
    ]

    top_items_rows = db.session.execute(
        select(
            Item.id, 
            Item.name, 
            Item.click_count, 
            Item.view_count,
            Item.save_count,
            Item.like_count
        )
        .where(Item.view_count > 10)
        .order_by((Item.click_count * 1.0 / Item.view_count).desc())
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
        "item_type_distribution": item_type_distribution,
        "top_engagement_items": top_engagement_items
    }

def load_admin_item_aggregates(page_ids):
    min_price_rows = db.session.execute(
        select(
            ItemVariant.item_id,
            func.min(ItemVariant.price).label("min_price"),
            func.max(ItemVariant.price).label("max_price"),
            ItemVariant.currency,
        )
        .where(ItemVariant.item_id.in_(page_ids), ItemVariant.price != None)
        .group_by(ItemVariant.item_id, ItemVariant.currency)
        .order_by(ItemVariant.item_id, func.min(ItemVariant.price))
    ).all()

    min_price_map: dict[int, dict] = {}
    for r in min_price_rows:
        if r.item_id not in min_price_map:
            min_price_map[r.item_id] = {
                "price": float(r.min_price), 
                "max_price": float(r.max_price) if r.max_price else None,
                "currency": r.currency
            }

    store_rows = db.session.execute(
        select(
            ItemVariant.item_id,
            func.count(ItemStoreLink.id).label("active_links"),
            func.max(ItemStoreLink.last_synced_at).label("last_synced_at"),
            func.max(ItemStoreLink.old_price).label("max_old_price")
        )
        .join(ItemStoreLink, ItemStoreLink.variant_id == ItemVariant.id)
        .where(
            ItemVariant.item_id.in_(page_ids),
            ItemStoreLink.is_active.is_(True),
        )
        .group_by(ItemVariant.item_id)
    ).all()

    store_info_map = {
        r.item_id: {
            "active_links": int(r.active_links),
            "last_synced_at": r.last_synced_at,
            "has_discount": r.max_old_price is not None and float(r.max_old_price) > 0
        }
        for r in store_rows
    }
    
    image_rows = db.session.execute(
        select(ItemImage.item_id, func.count(ItemImage.id).label("image_count"))
        .where(ItemImage.item_id.in_(page_ids))
        .group_by(ItemImage.item_id)
    ).all()
    image_info_map = {r.item_id: int(r.image_count) > 0 for r in image_rows}

    spec_rows = db.session.execute(
        select(ItemSpecification.item_id, func.count(ItemSpecification.id).label("spec_count"))
        .where(ItemSpecification.item_id.in_(page_ids))
        .group_by(ItemSpecification.item_id)
    ).all()
    spec_info_map = {r.item_id: int(r.spec_count) > 0 for r in spec_rows}

    return min_price_map, store_info_map, image_info_map, spec_info_map

def build_admin_items_query(args, sort_col, sort_dir):
    search        = args.get("search", "").strip()
    brand_slug    = args.get("brand")
    category_slug = args.get("category")
    source_slug   = args.get("source")
    has_images    = args.get("has_images")
    has_brand     = args.get("has_brand")
    availability  = args.get("availability")
    item_type     = args.get("item_type")

    stmt = select(Item).options(joinedload(Item.brand), joinedload(Item.category))

    if search:
        term = f"%{search}%"
        if search.isdigit():
            stmt = stmt.where(or_(Item.id == int(search), Item.name.ilike(term)))
        else:
            stmt = stmt.where(or_(Item.name.ilike(term), Item.description.ilike(term)))

    if brand_slug:
        stmt = stmt.join(Item.brand).where(Brand.slug == brand_slug)
    if category_slug:
        stmt = stmt.join(Item.category).where(Category.slug == category_slug)
    if source_slug:
        stmt = stmt.join(Item.source).where(Source.slug == source_slug)
    if item_type:
        stmt = stmt.where(Item.item_type == item_type)
        
    if has_images == "true":
        stmt = stmt.where(Item.images.any())
    elif has_images == "false":
        stmt = stmt.where(~Item.images.any())
        
    if has_brand == "true":
        stmt = stmt.where(Item.brand_id.isnot(None))
    elif has_brand == "false":
        stmt = stmt.where(Item.brand_id.is_(None))
        
    if availability and availability != "all":
        stmt = stmt.where(
            Item.variants.any(
                ItemVariant.store_links.any(
                    (ItemStoreLink.is_active == True) & (ItemStoreLink.availability == availability)
                )
            )
        )

    if sort_col == "min_price":
        price_sub = select(func.min(ItemVariant.price)).where(ItemVariant.item_id == Item.id).scalar_subquery()
        stmt = stmt.order_by(price_sub.asc() if sort_dir == "asc" else price_sub.desc())
    elif sort_col == "store_count":
        store_sub = select(func.count(ItemStoreLink.id)).join(ItemVariant, ItemVariant.id == ItemStoreLink.variant_id).where(ItemVariant.item_id == Item.id, ItemStoreLink.is_active == True).scalar_subquery()
        stmt = stmt.order_by(store_sub.asc() if sort_dir == "asc" else store_sub.desc())
    elif sort_col == "last_synced_at":
        sync_sub = select(func.max(ItemStoreLink.last_synced_at)).join(ItemVariant, ItemVariant.id == ItemStoreLink.variant_id).where(ItemVariant.item_id == Item.id).scalar_subquery()
        stmt = stmt.order_by(sync_sub.asc() if sort_dir == "asc" else sync_sub.desc())
    else:
        stmt = stmt.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())

    return stmt

def get_admin_items_page(args, sort_col, sort_dir, page, per_page):
    stmt = build_admin_items_query(args, sort_col, sort_dir)
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)

def get_admin_item(id):
    return db.session.get(Item, id)

def _calculate_item_completeness_score(item, price_info, store_info, has_image, has_specs):
    completeness_points = 0
    total_criteria = 8
    if has_image: completeness_points += 1
    if item.brand_id: completeness_points += 1
    if item.description and len(item.description) > 10: completeness_points += 1
    if store_info.get("active_links", 0) > 0: completeness_points += 1
    if price_info.get("price") is not None: completeness_points += 1
    if has_specs: completeness_points += 1
    if item.searchable_attributes and len(item.searchable_attributes) > 0: completeness_points += 1
    if item.structured_details and len(item.structured_details) > 0: completeness_points += 1
    
    return int((completeness_points / total_criteria) * 100)

def serialize_item_row(item, price_info, store_info, has_image, has_specs):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    
    price_min = price_info.get("price")
    price_max = price_info.get("max_price")
    currency = price_info.get("currency")

    sync_age_days = None
    last_synced_at = store_info.get("last_synced_at")
    if last_synced_at:
        if last_synced_at.tzinfo is None:
            last_synced_at = last_synced_at.replace(tzinfo=timezone.utc)
        sync_age_days = (now - last_synced_at).days

    completeness_score = _calculate_item_completeness_score(item, price_info, store_info, has_image, has_specs)

    return {
        "id":          item.id,
        "name":        item.name,
        "slug":        item.slug,
        "image_url":   item.image_url if has_image else None,
        "brand":       item.brand.name if item.brand else "—",
        "brand_slug":  item.brand.slug if item.brand else None,
        "category":    item.category.name if item.category else "—",
        "category_slug": item.category.slug if item.category else None,
        "category_name": item.category.name if item.category else None,
        "brand_name":  item.brand.name if item.brand else None,
        "min_price":   price_min,
        "max_price":   price_max,
        "currency":    currency,
        "store_count": store_info.get("active_links", 0),
        "last_synced_at": store_info.get("last_synced_at").isoformat() if store_info.get("last_synced_at") else None,
        "sync_age":    sync_age_days,
        "has_discount": store_info.get("has_discount", False),
        "health":      completeness_score,
        "click_count": item.click_count or 0,
        "view_count":  item.view_count or 0,
        "created_at":  item.created_at.isoformat() if item.created_at else None,
    }

def get_admin_item_inspect_raw(id):
    item = db.session.scalar(
        select(Item).options(
            joinedload(Item.category),
            joinedload(Item.brand),
            joinedload(Item.source),
            selectinload(Item.variants).selectinload(ItemVariant.store_links).joinedload(ItemStoreLink.store),
            selectinload(Item.linked_contents),
            selectinload(Item.images),
            selectinload(Item.specifications),
            selectinload(Item.comments).joinedload(Comment.user)
        ).where(Item.id == id)
    )
    return item

def get_admin_store_inspect_raw(id):
    from sqlalchemy import select, func, case
    from datetime import datetime, timezone, timedelta
    from app.domains.item.models import Store, ItemStoreLink, ItemVariant
    
    store = db.session.get(Store, id)
    if not store:
        return None
        
    product_count = db.session.scalar(
        select(func.count(func.distinct(ItemVariant.item_id)))
        .join(ItemStoreLink, ItemStoreLink.variant_id == ItemVariant.id)
        .where(ItemStoreLink.store_id == id)
    ) or 0
    
    now = datetime.now(timezone.utc)
    stale_date = now - timedelta(days=7)

    stats = db.session.execute(
        select(
            func.count(ItemStoreLink.id).label("total_links"),
            func.sum(case((ItemStoreLink.is_active == True, 1), else_=0)).label("active_links"),
            func.sum(case((ItemStoreLink.is_active == False, 1), else_=0)).label("inactive_links"),
            func.sum(case((ItemStoreLink.last_synced_at == None, 1), else_=0)).label("never_synced"),
            func.sum(case((ItemStoreLink.last_synced_at < stale_date, 1), else_=0)).label("stale_links"),
            func.sum(case((ItemStoreLink.availability == 'OutOfStock', 1), else_=0)).label("out_of_stock"),
            func.max(ItemStoreLink.last_synced_at).label("last_synced"),
            func.count(func.distinct(ItemStoreLink.program_name)).label("program_count"),
            func.avg(ItemStoreLink.commission_rate).label("avg_commission"),
            func.max(ItemStoreLink.commission_rate).label("max_commission"),
            func.sum(case((ItemStoreLink.commission_rate != None, 1), else_=0)).label("with_commission"),
            func.sum(case((ItemStoreLink.commission_rate == None, 1), else_=0)).label("without_commission"),
            func.sum(case((ItemStoreLink.tracking_code != None, 1), else_=0)).label("with_tracking"),
            func.min(ItemStoreLink.price).label("min_price"),
            func.avg(ItemStoreLink.price).label("avg_price"),
            func.max(ItemStoreLink.price).label("max_price"),
            func.sum(case(((ItemStoreLink.old_price != None) & (ItemStoreLink.old_price > ItemStoreLink.price), 1), else_=0)).label("with_discount"),
            func.avg(case(((ItemStoreLink.old_price != None) & (ItemStoreLink.old_price > ItemStoreLink.price), (ItemStoreLink.old_price - ItemStoreLink.price) / ItemStoreLink.old_price * 100), else_=None)).label("avg_discount_pct"),
            func.sum(case((ItemStoreLink.price == None, 1), else_=0)).label("null_price")
        )
        .where(ItemStoreLink.store_id == id)
    ).first()
    
    currency_mix_rows = db.session.execute(
        select(ItemStoreLink.currency, func.count(ItemStoreLink.id))
        .where(ItemStoreLink.store_id == id)
        .where(ItemStoreLink.currency != None)
        .group_by(ItemStoreLink.currency)
    ).all()
    currency_mix_list = [{"label": c[0], "detail": c[1]} for c in currency_mix_rows] if currency_mix_rows else []

    all_syncs = db.session.execute(
        select(ItemStoreLink.last_synced_at)
        .where(ItemStoreLink.store_id == id)
        .where(ItemStoreLink.last_synced_at != None)
    ).all()
    total_days = 0
    for (dt,) in all_syncs:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        total_days += (now - dt).days
    avg_sync_age = round(total_days / len(all_syncs), 1) if all_syncs else None

    return store, stats, product_count, currency_mix_list, avg_sync_age

