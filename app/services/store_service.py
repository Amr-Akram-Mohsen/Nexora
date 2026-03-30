from datetime import datetime, timedelta
from app.models import ItemClick, View, db
from sqlalchemy import func
from app.constants import TargetType
# --- weights for scoring ---
PRICE_WEIGHT = 0.7
CTR_WEIGHT = 0.3
FRESHNESS_HOURS = 24  # optional: boost links added in last 24h

def calculate_link_score(link):
    """
    Calculate a score for the link based on price, CTR, and freshness.
    Higher score = better link.
    """
    # Price component: normalized, lower price = higher score
    price_score = 1 / (float(link.price) if link.price is not None else 1e9)

    # CTR component
    ctr_score = link.ctr if link.ctr else 0

    # Freshness component: small bonus if link is new
    freshness_score = 0
    if link.created_at:
        hours_since_added = (datetime.utcnow() - link.created_at).total_seconds() / 3600
        if hours_since_added <= FRESHNESS_HOURS:
            freshness_score = 0.05  # small boost

    # weighted total score
    total_score = (PRICE_WEIGHT * price_score) + (CTR_WEIGHT * ctr_score) + freshness_score
    return total_score


def prepare_store_links(item):
    """
    Prepare item.store_links for display:
    - Only active links
    - Compute last-24h CTR
    - Assign best_link (cheapest) and top_pick (highest CTR)
    - Compute a total link score combining price + CTR + freshness
    - Sort links for display based on total_score
    """
    # --- STEP 0: active links ---
    links = [l for l in (item.store_links or []) if l.is_active]
    if not links:
        return []

    # --- STEP 1: clicks in last 24h ---
    last_24h = datetime.utcnow() - timedelta(hours=24)
    clicks_data = db.session.query(
        ItemClick.item_store_link_id,
        func.count(func.distinct(
            func.coalesce(ItemClick.user_id, ItemClick.ip_address)
        ))
    ).filter(
        ItemClick.item_store_link_id.in_([l.id for l in links]),
        ItemClick.created_at >= last_24h
    ).group_by(ItemClick.item_store_link_id).all()
    click_counts = dict(clicks_data)

    # --- STEP 2: item views last 24h ---
    item_view_count_24h = db.session.query(
        func.count(func.distinct(
            func.coalesce(View.user_id, View.ip_address)
        ))
    ).filter(
        View.target_type == TargetType.PRODUCT,
        View.target_id == item.id,
        View.created_at >= last_24h
    ).scalar() or 0

    # --- STEP 3: reset link flags and assign clicks & CTR ---
    for link in links:
        link.best_link = False
        link.top_pick = False
        link.clicks = click_counts.get(link.id, 0)
        link.ctr = (link.clicks / item_view_count_24h) if item_view_count_24h else 0

    # --- STEP 4: identify best (cheapest) and top pick (highest CTR) ---
    best_link = min(links, key=lambda l: l.price if l.price is not None else 1e9)
    top_pick = max(links, key=lambda l: l.ctr, default=None)
    if best_link:
        best_link.best_link = True
    if top_pick:
        top_pick.top_pick = True

    # --- STEP 5: compute total score for each link ---
    for link in links:
        link.score = calculate_link_score(link)

    # --- STEP 6: sort links descending by score ---
    links.sort(key=lambda l: l.score, reverse=True)

    return links

