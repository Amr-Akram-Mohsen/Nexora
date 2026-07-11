from sqlalchemy import select, func, or_, case
from app.core.extensions import db
from app.domains.product.models import Store, Product, ProductVariant, ProductStoreLink
from app.domains.interaction.models import View, ProductClick
from datetime import datetime, timezone, timedelta

def _build_sync_cadence(recent_syncs, now):
    sync_cadence_map = {}
    for d in range(30):
        day_str = (now - timedelta(days=d)).strftime('%Y-%m-%d')
        sync_cadence_map[day_str] = 0
        
    for dt in recent_syncs:
        if dt:
            day_str = dt.strftime('%Y-%m-%d')
            if day_str in sync_cadence_map:
                sync_cadence_map[day_str] += 1
    
    return [{"date": k, "count": v} for k, v in sorted(sync_cadence_map.items())]

def _calculate_store_sync_ages(store_syncs, now):
    store_age_map = {}
    for name, dt in store_syncs:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age = (now - dt).days
        if name not in store_age_map:
            store_age_map[name] = []
        store_age_map[name].append(age)
        
    avg_sync_age_by_store = []
    for name, ages in store_age_map.items():
        avg_age = sum(ages) / len(ages) if ages else 0
        avg_sync_age_by_store.append({"name": name, "avg_age_days": round(avg_age, 1)})
        
    avg_sync_age_by_store.sort(key=lambda x: x["avg_age_days"], reverse=True)
    return avg_sync_age_by_store

def _build_price_staleness_grid(staleness_query, stale_date):
    staleness_map = {}
    for store_name, synced_at in staleness_query:
        if store_name not in staleness_map:
            staleness_map[store_name] = {"fresh": 0, "stale": 0}
            
        if synced_at:
            if synced_at.tzinfo is None:
                synced_at = synced_at.replace(tzinfo=timezone.utc)
            if synced_at >= stale_date:
                staleness_map[store_name]["fresh"] += 1
            else:
                staleness_map[store_name]["stale"] += 1
        else:
            staleness_map[store_name]["stale"] += 1
            
    staleness_list = [
        {"name": k, "fresh": v["fresh"], "stale": v["stale"], "total": v["fresh"] + v["stale"]} 
        for k, v in staleness_map.items()
    ]
    staleness_list.sort(key=lambda x: x["total"], reverse=True)
    return staleness_list[:10]

def get_admin_stores_page(page, per_page, search, network, country, sync_staleness):
    stmt = select(Store)
    if search:
        term = f"%{search}%"
        stmt = stmt.where(or_(
            Store.name.ilike(term),
            Store.slug.ilike(term),
            Store.website.ilike(term),
        ))
        
    if network:
        stmt = stmt.where(Store.affiliate_network == network)
    if country:
        stmt = stmt.where(Store.country == country)
        
    if sync_staleness:
        now = datetime.now(timezone.utc)
        stale_date = now - timedelta(days=7)
        if sync_staleness == "fresh":
            stmt = stmt.where(Store.product_links.any(ProductStoreLink.last_synced_at >= stale_date))
        elif sync_staleness == "stale":
            stmt = stmt.where(Store.product_links.any(ProductStoreLink.last_synced_at < stale_date))
        elif sync_staleness == "never":
            stmt = stmt.where(Store.product_links.any(ProductStoreLink.last_synced_at == None))

    stmt = stmt.order_by(Store.name.asc())
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    page_store_ids = [st.id for st in pagination.products]

    if page_store_ids:
        product_count_rows = db.session.execute(
            select(
                ProductStoreLink.store_id,
                func.count(func.distinct(ProductVariant.product_id)).label("product_count"),
            )
            .join(ProductVariant, ProductVariant.id == ProductStoreLink.variant_id)
            .where(ProductStoreLink.store_id.in_(page_store_ids))
            .group_by(ProductStoreLink.store_id)
        ).all()
        product_count_map = {r.store_id: r.product_count for r in product_count_rows}

        clicks_rows = db.session.execute(
            select(ProductStoreLink.store_id, func.count(ProductClick.id).label("clicks"))
            .join(ProductClick, ProductClick.product_store_link_id == ProductStoreLink.id)
            .where(ProductStoreLink.store_id.in_(page_store_ids))
            .group_by(ProductStoreLink.store_id)
        ).all()
        clicks_map = {r.store_id: r.clicks for r in clicks_rows}

        views_rows_q = db.session.execute(
            select(ProductStoreLink.store_id, func.count(func.distinct(View.id)).label("views"))
            .join(ProductVariant, ProductVariant.id == ProductStoreLink.variant_id)
            .join(View, (View.target_id == ProductVariant.product_id) & (View.target_type == 'product'))
            .where(ProductStoreLink.store_id.in_(page_store_ids))
            .group_by(ProductStoreLink.store_id)
        ).all()
        views_map = {r.store_id: r.views for r in views_rows_q}

        latest_activity_rows = db.session.execute(
            select(
                ProductStoreLink.store_id,
                func.max(Product.created_at).label("latest_created_at"),
            )
            .join(ProductVariant, ProductVariant.id == ProductStoreLink.variant_id)
            .join(Product, Product.id == ProductVariant.product_id)
            .where(ProductStoreLink.store_id.in_(page_store_ids))
            .group_by(ProductStoreLink.store_id)
        ).all()
        latest_activity_map = {r.store_id: r.latest_created_at for r in latest_activity_rows}

        avg_comm_rows = db.session.execute(
            select(ProductStoreLink.store_id, func.avg(ProductStoreLink.commission_rate).label("avg_comm"))
            .where(ProductStoreLink.store_id.in_(page_store_ids))
            .where(ProductStoreLink.commission_rate != None)
            .group_by(ProductStoreLink.store_id)
        ).all()
        avg_comm_map = {r.store_id: r.avg_comm for r in avg_comm_rows}

        sync_age_rows = db.session.execute(
            select(
                ProductStoreLink.store_id,
                func.max(ProductStoreLink.last_synced_at).label("last_synced")
            )
            .where(ProductStoreLink.store_id.in_(page_store_ids))
            .group_by(ProductStoreLink.store_id)
        ).all()
        sync_age_map = {r.store_id: r.last_synced for r in sync_age_rows}

        oos_rows = db.session.execute(
            select(
                ProductStoreLink.store_id,
                func.sum(case((ProductStoreLink.availability == 'OutOfStock', 1), else_=0)).label("oos_count"),
                func.count(ProductStoreLink.id).label("total_links"),
                func.sum(case((ProductStoreLink.is_active == True, 1), else_=0)).label("active_links")
            )
            .where(ProductStoreLink.store_id.in_(page_store_ids))
            .group_by(ProductStoreLink.store_id)
        ).all()
        oos_map = {r.store_id: {"oos_count": r.oos_count, "total_links": r.total_links, "active_links": r.active_links} for r in oos_rows}
    else:
        product_count_map, clicks_map, views_map, latest_activity_map, avg_comm_map, sync_age_map, oos_map = {}, {}, {}, {}, {}, {}, {}

    now = datetime.now(timezone.utc)
    
    serialized = []
    for st in pagination.products:
        product_count   = product_count_map.get(st.id, 0)
        latest_activity = latest_activity_map.get(st.id)
        clicks          = clicks_map.get(st.id, 0)
        views           = views_map.get(st.id, 0)
        avg_comm        = avg_comm_map.get(st.id)
        last_synced     = sync_age_map.get(st.id)
        oos_data        = oos_map.get(st.id, {"oos_count": 0, "total_links": 0, "active_links": 0})
        
        ctr = 0.0
        if views > 0 and views >= clicks:
             ctr = round((clicks / views) * 100.0, 2)
             
        sync_age_days = None
        if last_synced:
            if last_synced.tzinfo is None:
                last_synced = last_synced.replace(tzinfo=timezone.utc)
            sync_age_days = (now - last_synced).days
            
        oos_rate = 0.0
        if oos_data["total_links"] > 0:
            oos_rate = round((oos_data["oos_count"] / oos_data["total_links"]) * 100.0, 1)

        if not st.is_active:
            status_val = "failed"
        elif product_count == 0:
            status_val = "warning"
        else:
            status_val = "healthy"
            
        serialized.append({
            "id":                  st.id,
            "name":                st.name,
            "website":             st.website,
            "affiliate_network":   st.affiliate_network,
            "product_count":       product_count,
            "clicks":              clicks,
            "ctr":                 ctr,
            "active_links":        oos_data["active_links"],
            "sync_age":            sync_age_days,
            "oos_rate":            oos_rate,
            "avg_commission":      float(avg_comm) if avg_comm is not None else None,
            "status":              status_val,
            "slug":                st.slug,
        })
    return pagination, serialized

def get_admin_store_health_stats():
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    
    total_links = db.session.scalar(select(func.count(ProductStoreLink.id))) or 0
    active_links = db.session.scalar(select(func.count(ProductStoreLink.id)).where(ProductStoreLink.is_active == True)) or 0
    
    synced_today = db.session.scalar(
        select(func.count(ProductStoreLink.id))
        .where(ProductStoreLink.last_synced_at >= today_start)
    ) or 0
    
    synced_this_week = db.session.scalar(
        select(func.count(ProductStoreLink.id))
        .where(ProductStoreLink.last_synced_at >= week_start)
    ) or 0
    
    never_synced = db.session.scalar(
        select(func.count(ProductStoreLink.id))
        .where(ProductStoreLink.last_synced_at.is_(None))
    ) or 0
    
    out_of_stock = db.session.scalar(
        select(func.count(ProductStoreLink.id))
        .where(ProductStoreLink.availability == 'OutOfStock')
    ) or 0
    
    oos_stores_rows = db.session.execute(
        select(Store.name, func.count(ProductStoreLink.id))
        .join(ProductStoreLink, ProductStoreLink.store_id == Store.id)
        .where(ProductStoreLink.availability == 'OutOfStock')
        .group_by(Store.name)
        .order_by(func.count(ProductStoreLink.id).desc())
        .limit(5)
    ).all()
    
    oos_by_store = [{"name": r[0], "count": r[1]} for r in oos_stores_rows]
    
    month_start = now - timedelta(days=30)
    
    checked_in_24h = db.session.scalar(
        select(func.count(ProductStoreLink.id))
        .where(ProductStoreLink.last_checked_at >= today_start)
    ) or 0
    
    deeplink_refreshed_30d = db.session.scalar(
        select(func.count(ProductStoreLink.id))
        .where(ProductStoreLink.deeplink_generated_at >= month_start)
    ) or 0
    
    never_checked = db.session.scalar(
        select(func.count(ProductStoreLink.id))
        .where(ProductStoreLink.last_checked_at.is_(None))
    ) or 0
    
    never_had_deeplink = db.session.scalar(
        select(func.count(ProductStoreLink.id))
        .where(ProductStoreLink.deeplink_generated_at.is_(None))
    ) or 0
    
    avail_rows = db.session.execute(
        select(ProductStoreLink.availability, func.count(ProductStoreLink.id))
        .group_by(ProductStoreLink.availability)
    ).all()
    
    availability_breakdown = {r[0] if r[0] else 'Unknown': r[1] for r in avail_rows}
    for state in ['InStock', 'OutOfStock', 'PreOrder', 'Unknown']:
        if state not in availability_breakdown:
            availability_breakdown[state] = 0

    recent_syncs = db.session.scalars(
        select(ProductStoreLink.last_synced_at)
        .where(ProductStoreLink.last_synced_at >= month_start)
    ).all()
    
    sync_cadence = _build_sync_cadence(recent_syncs, now)

    store_syncs = db.session.execute(
        select(Store.name, ProductStoreLink.last_synced_at)
        .join(ProductStoreLink, ProductStoreLink.store_id == Store.id)
        .where(ProductStoreLink.last_synced_at != None)
    ).all()
    
    avg_sync_age_by_store = _calculate_store_sync_ages(store_syncs, now)
    top_stale_stores = avg_sync_age_by_store[:10]
    
    return {
        "total_links": total_links,
        "active_links": active_links,
        "synced_today": synced_today,
        "synced_this_week": synced_this_week,
        "never_synced": never_synced,
        "out_of_stock": out_of_stock,
        "oos_by_store": oos_by_store,
        "checked_in_24h": checked_in_24h,
        "deeplink_refreshed_30d": deeplink_refreshed_30d,
        "never_checked": never_checked,
        "never_had_deeplink": never_had_deeplink,
        "availability_breakdown": availability_breakdown,
        "sync_cadence": sync_cadence,
        "avg_sync_age_by_store": avg_sync_age_by_store,
        "top_stale_stores": top_stale_stores
    }

def get_admin_store_coverage_stats():
    coverage_rows = db.session.execute(
        select(Store.name, func.count(func.distinct(Product.category_id)))
        .join(ProductStoreLink, ProductStoreLink.store_id == Store.id)
        .join(ProductVariant, ProductVariant.id == ProductStoreLink.variant_id)
        .join(Product, Product.id == ProductVariant.product_id)
        .group_by(Store.name)
        .order_by(func.count(func.distinct(Product.category_id)).desc())
    ).all()
    
    category_coverage = [{"name": r[0], "count": r[1]} for r in coverage_rows]
    
    commission_rows = db.session.execute(
        select(Store.name, func.avg(ProductStoreLink.commission_rate))
        .join(ProductStoreLink, ProductStoreLink.store_id == Store.id)
        .where(ProductStoreLink.commission_rate != None)
        .group_by(Store.name)
        .order_by(func.avg(ProductStoreLink.commission_rate).desc())
    ).all()
    
    commission_rates = [{"name": r[0], "avg_rate": round(float(r[1]), 2)} for r in commission_rows]
    
    return category_coverage, commission_rates

def get_admin_store_affiliate_stats():
    now = datetime.now(timezone.utc)
    
    links_with_commission = db.session.scalar(select(func.count(ProductStoreLink.id)).where(ProductStoreLink.commission_rate != None)) or 0
    links_without_commission = db.session.scalar(select(func.count(ProductStoreLink.id)).where(ProductStoreLink.commission_rate == None)) or 0
    avg_commission_rate_scalar = db.session.scalar(select(func.avg(ProductStoreLink.commission_rate)))
    avg_commission_rate = round(float(avg_commission_rate_scalar), 2) if avg_commission_rate_scalar else 0.0
    
    program_rows = db.session.execute(
        select(ProductStoreLink.program_name, func.count(ProductStoreLink.id))
        .where(ProductStoreLink.program_name != None)
        .group_by(ProductStoreLink.program_name)
        .order_by(func.count(ProductStoreLink.id).desc())
        .limit(10)
    ).all()
    
    program_distribution = [{"name": r[0] if r[0] else 'Unknown', "count": r[1]} for r in program_rows]
    top_program = program_distribution[0]["name"] if program_distribution else "None"
    
    commission_rows = db.session.execute(
        select(Store.name, func.avg(ProductStoreLink.commission_rate))
        .join(ProductStoreLink, ProductStoreLink.store_id == Store.id)
        .where(ProductStoreLink.commission_rate != None)
        .group_by(Store.name)
        .order_by(func.avg(ProductStoreLink.commission_rate).desc())
        .limit(10)
    ).all()
    commission_rate_ranking = [{"name": r[0], "avg_rate": round(float(r[1]), 2)} for r in commission_rows]
    
    with_tracking = db.session.scalar(select(func.count(ProductStoreLink.id)).where(ProductStoreLink.tracking_code != None)) or 0
    without_tracking = db.session.scalar(select(func.count(ProductStoreLink.id)).where(ProductStoreLink.tracking_code == None)) or 0
    tracking_coverage = {
        "With Tracking": with_tracking,
        "Without Tracking": without_tracking
    }
    
    fresh_date = now - timedelta(days=7)
    stale_date = now - timedelta(days=30)
    
    fresh = db.session.scalar(select(func.count(ProductStoreLink.id)).where(ProductStoreLink.deeplink_generated_at >= fresh_date)) or 0
    aging = db.session.scalar(select(func.count(ProductStoreLink.id)).where(ProductStoreLink.deeplink_generated_at >= stale_date).where(ProductStoreLink.deeplink_generated_at < fresh_date)) or 0
    stale = db.session.scalar(select(func.count(ProductStoreLink.id)).where(ProductStoreLink.deeplink_generated_at < stale_date)) or 0
    never = db.session.scalar(select(func.count(ProductStoreLink.id)).where(ProductStoreLink.deeplink_generated_at == None)) or 0
    
    deeplink_freshness = {
        "Fresh (<7d)": fresh,
        "Aging (7-30d)": aging,
        "Stale (>30d)": stale,
        "Never": never
    }
    
    return {
        "links_with_commission": links_with_commission,
        "links_without_commission": links_without_commission,
        "avg_commission_rate": avg_commission_rate,
        "top_program": top_program,
        "program_distribution": program_distribution,
        "commission_rate_ranking": commission_rate_ranking,
        "tracking_coverage": tracking_coverage,
        "deeplink_freshness": deeplink_freshness
    }

def get_admin_store_pricing_stats():
    now = datetime.now(timezone.utc)
    stale_date = now - timedelta(days=7)
    
    null_price_count = db.session.scalar(select(func.count(ProductStoreLink.id)).where(ProductStoreLink.price == None)) or 0
    stale_price_count = db.session.scalar(select(func.count(ProductStoreLink.id)).where(ProductStoreLink.last_synced_at < stale_date)) or 0
    
    avg_discount_scalar = db.session.scalar(
        select(func.avg(((ProductStoreLink.old_price - ProductStoreLink.price) / ProductStoreLink.old_price) * 100.0))
        .where(ProductStoreLink.old_price != None)
        .where(ProductStoreLink.price != None)
        .where(ProductStoreLink.old_price > ProductStoreLink.price)
        .where(ProductStoreLink.old_price > 0)
    )
    avg_discount_percentage = round(float(avg_discount_scalar), 1) if avg_discount_scalar else 0.0

    currency_rows = db.session.execute(
        select(ProductVariant.currency, func.count(ProductStoreLink.id))
        .join(ProductVariant, ProductVariant.id == ProductStoreLink.variant_id)
        .where(ProductVariant.currency != None)
        .group_by(ProductVariant.currency)
    ).all()
    currency_mix = {r[0] if r[0] else 'Unknown': r[1] for r in currency_rows}

    discount_rows = db.session.execute(
        select(
            Store.name, 
            func.avg(((ProductStoreLink.old_price - ProductStoreLink.price) / ProductStoreLink.old_price) * 100.0)
        )
        .join(ProductStoreLink, ProductStoreLink.store_id == Store.id)
        .where(ProductStoreLink.old_price != None)
        .where(ProductStoreLink.price != None)
        .where(ProductStoreLink.old_price > ProductStoreLink.price)
        .where(ProductStoreLink.old_price > 0)
        .group_by(Store.name)
        .order_by(func.avg(((ProductStoreLink.old_price - ProductStoreLink.price) / ProductStoreLink.old_price) * 100.0).desc())
        .limit(5)
    ).all()
    discount_depth_ranking = [{"name": r[0], "avg_discount": round(float(r[1]), 1)} for r in discount_rows]

    staleness_query = db.session.execute(
        select(Store.name, ProductStoreLink.last_synced_at)
        .join(ProductStoreLink, ProductStoreLink.store_id == Store.id)
    ).all()
    
    price_staleness_grid = _build_price_staleness_grid(staleness_query, stale_date)

    item_avail_query = db.session.execute(
        select(ProductVariant.product_id, ProductStoreLink.availability)
        .join(ProductStoreLink, ProductStoreLink.variant_id == ProductVariant.id)
    ).all()
    
    item_avail_map = {}
    for product_id, avail in item_avail_query:
        if product_id not in item_avail_map:
            item_avail_map[product_id] = {"total": 0, "oos": 0}
        item_avail_map[product_id]["total"] += 1
        if avail == 'OutOfStock':
            item_avail_map[product_id]["oos"] += 1
            
    all_oos_items_count = sum(1 for v in item_avail_map.values() if v["total"] > 0 and v["total"] == v["oos"])

    store_price_query = db.session.execute(
        select(Store.name, ProductStoreLink.price)
        .join(ProductStoreLink, ProductStoreLink.store_id == Store.id)
    ).all()
    
    store_price_map = {}
    for name, price in store_price_query:
        if name not in store_price_map:
            store_price_map[name] = {"total": 0, "nulls": 0}
        store_price_map[name]["total"] += 1
        if price is None:
            store_price_map[name]["nulls"] += 1
            
    high_null_price_stores = []
    for name, stats in store_price_map.items():
        if stats["total"] >= 5:
            null_rate = (stats["nulls"] / stats["total"]) * 100
            if null_rate > 20.0:
                high_null_price_stores.append({"name": name, "null_rate": round(null_rate, 1)})

    return {
        "null_price_count": null_price_count,
        "stale_price_count": stale_price_count,
        "avg_discount_percentage": avg_discount_percentage,
        "currency_mix": currency_mix,
        "discount_depth_ranking": discount_depth_ranking,
        "price_staleness_grid": price_staleness_grid,
        "all_oos_items_count": all_oos_items_count,
        "high_null_price_stores": high_null_price_stores
    }


