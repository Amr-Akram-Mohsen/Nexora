from sqlalchemy import select, func, or_, case
from app.core.extensions import db
from app.domains.item.models import Store, Item, ItemVariant, ItemStoreLink
from app.domains.interaction.models import View, ItemClick
from datetime import datetime, timezone, timedelta

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
            stmt = stmt.where(Store.item_links.any(ItemStoreLink.last_synced_at >= stale_date))
        elif sync_staleness == "stale":
            stmt = stmt.where(Store.item_links.any(ItemStoreLink.last_synced_at < stale_date))
        elif sync_staleness == "never":
            stmt = stmt.where(Store.item_links.any(ItemStoreLink.last_synced_at == None))

    stmt = stmt.order_by(Store.name.asc())
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    page_store_ids = [st.id for st in pagination.items]

    if page_store_ids:
        product_count_rows = db.session.execute(
            select(
                ItemStoreLink.store_id,
                func.count(func.distinct(ItemVariant.item_id)).label("product_count"),
            )
            .join(ItemVariant, ItemVariant.id == ItemStoreLink.variant_id)
            .where(ItemStoreLink.store_id.in_(page_store_ids))
            .group_by(ItemStoreLink.store_id)
        ).all()
        product_count_map = {r.store_id: r.product_count for r in product_count_rows}

        clicks_rows = db.session.execute(
            select(ItemStoreLink.store_id, func.count(ItemClick.id).label("clicks"))
            .join(ItemClick, ItemClick.item_store_link_id == ItemStoreLink.id)
            .where(ItemStoreLink.store_id.in_(page_store_ids))
            .group_by(ItemStoreLink.store_id)
        ).all()
        clicks_map = {r.store_id: r.clicks for r in clicks_rows}

        views_rows_q = db.session.execute(
            select(ItemStoreLink.store_id, func.count(func.distinct(View.id)).label("views"))
            .join(ItemVariant, ItemVariant.id == ItemStoreLink.variant_id)
            .join(View, (View.target_id == ItemVariant.item_id) & (View.target_type == 'item'))
            .where(ItemStoreLink.store_id.in_(page_store_ids))
            .group_by(ItemStoreLink.store_id)
        ).all()
        views_map = {r.store_id: r.views for r in views_rows_q}

        latest_activity_rows = db.session.execute(
            select(
                ItemStoreLink.store_id,
                func.max(Item.created_at).label("latest_created_at"),
            )
            .join(ItemVariant, ItemVariant.id == ItemStoreLink.variant_id)
            .join(Item, Item.id == ItemVariant.item_id)
            .where(ItemStoreLink.store_id.in_(page_store_ids))
            .group_by(ItemStoreLink.store_id)
        ).all()
        latest_activity_map = {r.store_id: r.latest_created_at for r in latest_activity_rows}

        avg_comm_rows = db.session.execute(
            select(ItemStoreLink.store_id, func.avg(ItemStoreLink.commission_rate).label("avg_comm"))
            .where(ItemStoreLink.store_id.in_(page_store_ids))
            .where(ItemStoreLink.commission_rate != None)
            .group_by(ItemStoreLink.store_id)
        ).all()
        avg_comm_map = {r.store_id: r.avg_comm for r in avg_comm_rows}

        sync_age_rows = db.session.execute(
            select(
                ItemStoreLink.store_id,
                func.max(ItemStoreLink.last_synced_at).label("last_synced")
            )
            .where(ItemStoreLink.store_id.in_(page_store_ids))
            .group_by(ItemStoreLink.store_id)
        ).all()
        sync_age_map = {r.store_id: r.last_synced for r in sync_age_rows}

        oos_rows = db.session.execute(
            select(
                ItemStoreLink.store_id,
                func.sum(case((ItemStoreLink.availability == 'OutOfStock', 1), else_=0)).label("oos_count"),
                func.count(ItemStoreLink.id).label("total_links"),
                func.sum(case((ItemStoreLink.is_active == True, 1), else_=0)).label("active_links")
            )
            .where(ItemStoreLink.store_id.in_(page_store_ids))
            .group_by(ItemStoreLink.store_id)
        ).all()
        oos_map = {r.store_id: {"oos_count": r.oos_count, "total_links": r.total_links, "active_links": r.active_links} for r in oos_rows}
    else:
        product_count_map, clicks_map, views_map, latest_activity_map, avg_comm_map, sync_age_map, oos_map = {}, {}, {}, {}, {}, {}, {}

    now = datetime.now(timezone.utc)
    
    serialized = []
    for st in pagination.items:
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
    
    total_links = db.session.scalar(select(func.count(ItemStoreLink.id))) or 0
    active_links = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.is_active == True)) or 0
    
    synced_today = db.session.scalar(
        select(func.count(ItemStoreLink.id))
        .where(ItemStoreLink.last_synced_at >= today_start)
    ) or 0
    
    synced_this_week = db.session.scalar(
        select(func.count(ItemStoreLink.id))
        .where(ItemStoreLink.last_synced_at >= week_start)
    ) or 0
    
    never_synced = db.session.scalar(
        select(func.count(ItemStoreLink.id))
        .where(ItemStoreLink.last_synced_at.is_(None))
    ) or 0
    
    out_of_stock = db.session.scalar(
        select(func.count(ItemStoreLink.id))
        .where(ItemStoreLink.availability == 'OutOfStock')
    ) or 0
    
    oos_stores_rows = db.session.execute(
        select(Store.name, func.count(ItemStoreLink.id))
        .join(ItemStoreLink, ItemStoreLink.store_id == Store.id)
        .where(ItemStoreLink.availability == 'OutOfStock')
        .group_by(Store.name)
        .order_by(func.count(ItemStoreLink.id).desc())
        .limit(5)
    ).all()
    
    oos_by_store = [{"name": r[0], "count": r[1]} for r in oos_stores_rows]
    
    month_start = now - timedelta(days=30)
    
    checked_in_24h = db.session.scalar(
        select(func.count(ItemStoreLink.id))
        .where(ItemStoreLink.last_checked_at >= today_start)
    ) or 0
    
    deeplink_refreshed_30d = db.session.scalar(
        select(func.count(ItemStoreLink.id))
        .where(ItemStoreLink.deeplink_generated_at >= month_start)
    ) or 0
    
    never_checked = db.session.scalar(
        select(func.count(ItemStoreLink.id))
        .where(ItemStoreLink.last_checked_at.is_(None))
    ) or 0
    
    never_had_deeplink = db.session.scalar(
        select(func.count(ItemStoreLink.id))
        .where(ItemStoreLink.deeplink_generated_at.is_(None))
    ) or 0
    
    avail_rows = db.session.execute(
        select(ItemStoreLink.availability, func.count(ItemStoreLink.id))
        .group_by(ItemStoreLink.availability)
    ).all()
    
    availability_breakdown = {r[0] if r[0] else 'Unknown': r[1] for r in avail_rows}
    for state in ['InStock', 'OutOfStock', 'PreOrder', 'Unknown']:
        if state not in availability_breakdown:
            availability_breakdown[state] = 0

    recent_syncs = db.session.scalars(
        select(ItemStoreLink.last_synced_at)
        .where(ItemStoreLink.last_synced_at >= month_start)
    ).all()
    
    sync_cadence_map = {}
    for d in range(30):
        day_str = (now - timedelta(days=d)).strftime('%Y-%m-%d')
        sync_cadence_map[day_str] = 0
        
    for dt in recent_syncs:
        if dt:
            day_str = dt.strftime('%Y-%m-%d')
            if day_str in sync_cadence_map:
                sync_cadence_map[day_str] += 1
    
    sync_cadence = [{"date": k, "count": v} for k, v in sorted(sync_cadence_map.items())]

    store_syncs = db.session.execute(
        select(Store.name, ItemStoreLink.last_synced_at)
        .join(ItemStoreLink, ItemStoreLink.store_id == Store.id)
        .where(ItemStoreLink.last_synced_at != None)
    ).all()
    
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
        select(Store.name, func.count(func.distinct(Item.category_id)))
        .join(ItemStoreLink, ItemStoreLink.store_id == Store.id)
        .join(ItemVariant, ItemVariant.id == ItemStoreLink.variant_id)
        .join(Item, Item.id == ItemVariant.item_id)
        .group_by(Store.name)
        .order_by(func.count(func.distinct(Item.category_id)).desc())
    ).all()
    
    category_coverage = [{"name": r[0], "count": r[1]} for r in coverage_rows]
    
    commission_rows = db.session.execute(
        select(Store.name, func.avg(ItemStoreLink.commission_rate))
        .join(ItemStoreLink, ItemStoreLink.store_id == Store.id)
        .where(ItemStoreLink.commission_rate != None)
        .group_by(Store.name)
        .order_by(func.avg(ItemStoreLink.commission_rate).desc())
    ).all()
    
    commission_rates = [{"name": r[0], "avg_rate": round(float(r[1]), 2)} for r in commission_rows]
    
    return category_coverage, commission_rates

def get_admin_store_affiliate_stats():
    now = datetime.now(timezone.utc)
    
    links_with_commission = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.commission_rate != None)) or 0
    links_without_commission = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.commission_rate == None)) or 0
    avg_commission_rate_scalar = db.session.scalar(select(func.avg(ItemStoreLink.commission_rate)))
    avg_commission_rate = round(float(avg_commission_rate_scalar), 2) if avg_commission_rate_scalar else 0.0
    
    program_rows = db.session.execute(
        select(ItemStoreLink.program_name, func.count(ItemStoreLink.id))
        .where(ItemStoreLink.program_name != None)
        .group_by(ItemStoreLink.program_name)
        .order_by(func.count(ItemStoreLink.id).desc())
        .limit(10)
    ).all()
    
    program_distribution = [{"name": r[0] if r[0] else 'Unknown', "count": r[1]} for r in program_rows]
    top_program = program_distribution[0]["name"] if program_distribution else "None"
    
    commission_rows = db.session.execute(
        select(Store.name, func.avg(ItemStoreLink.commission_rate))
        .join(ItemStoreLink, ItemStoreLink.store_id == Store.id)
        .where(ItemStoreLink.commission_rate != None)
        .group_by(Store.name)
        .order_by(func.avg(ItemStoreLink.commission_rate).desc())
        .limit(10)
    ).all()
    commission_rate_ranking = [{"name": r[0], "avg_rate": round(float(r[1]), 2)} for r in commission_rows]
    
    with_tracking = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.tracking_code != None)) or 0
    without_tracking = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.tracking_code == None)) or 0
    tracking_coverage = {
        "With Tracking": with_tracking,
        "Without Tracking": without_tracking
    }
    
    fresh_date = now - timedelta(days=7)
    stale_date = now - timedelta(days=30)
    
    fresh = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.deeplink_generated_at >= fresh_date)) or 0
    aging = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.deeplink_generated_at >= stale_date).where(ItemStoreLink.deeplink_generated_at < fresh_date)) or 0
    stale = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.deeplink_generated_at < stale_date)) or 0
    never = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.deeplink_generated_at == None)) or 0
    
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
    
    null_price_count = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.price == None)) or 0
    stale_price_count = db.session.scalar(select(func.count(ItemStoreLink.id)).where(ItemStoreLink.last_synced_at < stale_date)) or 0
    
    avg_discount_scalar = db.session.scalar(
        select(func.avg(((ItemStoreLink.old_price - ItemStoreLink.price) / ItemStoreLink.old_price) * 100.0))
        .where(ItemStoreLink.old_price != None)
        .where(ItemStoreLink.price != None)
        .where(ItemStoreLink.old_price > ItemStoreLink.price)
        .where(ItemStoreLink.old_price > 0)
    )
    avg_discount_percentage = round(float(avg_discount_scalar), 1) if avg_discount_scalar else 0.0

    currency_rows = db.session.execute(
        select(ItemVariant.currency, func.count(ItemStoreLink.id))
        .join(ItemVariant, ItemVariant.id == ItemStoreLink.variant_id)
        .where(ItemVariant.currency != None)
        .group_by(ItemVariant.currency)
    ).all()
    currency_mix = {r[0] if r[0] else 'Unknown': r[1] for r in currency_rows}

    discount_rows = db.session.execute(
        select(
            Store.name, 
            func.avg(((ItemStoreLink.old_price - ItemStoreLink.price) / ItemStoreLink.old_price) * 100.0)
        )
        .join(ItemStoreLink, ItemStoreLink.store_id == Store.id)
        .where(ItemStoreLink.old_price != None)
        .where(ItemStoreLink.price != None)
        .where(ItemStoreLink.old_price > ItemStoreLink.price)
        .where(ItemStoreLink.old_price > 0)
        .group_by(Store.name)
        .order_by(func.avg(((ItemStoreLink.old_price - ItemStoreLink.price) / ItemStoreLink.old_price) * 100.0).desc())
        .limit(5)
    ).all()
    discount_depth_ranking = [{"name": r[0], "avg_discount": round(float(r[1]), 1)} for r in discount_rows]

    staleness_query = db.session.execute(
        select(Store.name, ItemStoreLink.last_synced_at)
        .join(ItemStoreLink, ItemStoreLink.store_id == Store.id)
    ).all()
    
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
    price_staleness_grid = staleness_list[:10]

    item_avail_query = db.session.execute(
        select(ItemVariant.item_id, ItemStoreLink.availability)
        .join(ItemStoreLink, ItemStoreLink.variant_id == ItemVariant.id)
    ).all()
    
    item_avail_map = {}
    for item_id, avail in item_avail_query:
        if item_id not in item_avail_map:
            item_avail_map[item_id] = {"total": 0, "oos": 0}
        item_avail_map[item_id]["total"] += 1
        if avail == 'OutOfStock':
            item_avail_map[item_id]["oos"] += 1
            
    all_oos_items_count = sum(1 for v in item_avail_map.values() if v["total"] > 0 and v["total"] == v["oos"])

    store_price_query = db.session.execute(
        select(Store.name, ItemStoreLink.price)
        .join(ItemStoreLink, ItemStoreLink.store_id == Store.id)
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

def build_admin_store_inspect_data(id):
    store = db.session.get(Store, id)
    if not store:
        return None
        
    product_count = db.session.scalar(
        select(func.count(func.distinct(ItemVariant.item_id)))
        .join(ItemStoreLink, ItemStoreLink.variant_id == ItemVariant.id)
        .where(ItemStoreLink.store_id == id)
    ) or 0
    
    from datetime import datetime, timezone, timedelta
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

    data = {
        "id": store.id,
        "name": store.name,
        "slug": store.slug,
        "website": store.website,
        "status": "Active" if store.is_active else "Inactive",
        "affiliate network": store.affiliate_network,
        "product count": product_count,
        "active links": stats.active_links or 0,
        "avg commission": float(stats.avg_commission) if stats.avg_commission is not None else None,
        "country": store.country,
        "currency": store.currency,
        "api enabled": store.api_enabled,
        "total links": stats.total_links or 0,
        "inactive links": stats.inactive_links or 0,
        "never synced": stats.never_synced or 0,
        "stale links (7d)": stats.stale_links or 0,
        "out of stock": stats.out_of_stock or 0,
        "avg sync age (days)": avg_sync_age,
        "last synced at": stats.last_synced.isoformat() if stats.last_synced else None,
        "feed enabled": store.feed_enabled,
        "network slug": store.network_slug,
        "program count": stats.program_count or 0,
        "avg commission rate": float(stats.avg_commission) if stats.avg_commission is not None else None,
        "max commission rate": float(stats.max_commission) if stats.max_commission is not None else None,
        "links with commission": stats.with_commission or 0,
        "links without commission": stats.without_commission or 0,
        "links with tracking code": stats.with_tracking or 0,
        "min price": float(stats.min_price) if stats.min_price is not None else None,
        "avg price": float(stats.avg_price) if stats.avg_price is not None else None,
        "max price": float(stats.max_price) if stats.max_price is not None else None,
        "links with discount": stats.with_discount or 0,
        "avg discount %": float(stats.avg_discount_pct) if stats.avg_discount_pct is not None else None,
        "links with null price": stats.null_price or 0,
        "currency mix": currency_mix_list
    }
    return {
        "raw_data": data,
        "inspect_id": store.id
    }
