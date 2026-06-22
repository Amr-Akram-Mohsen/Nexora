# app/admin/recommendations.py
"""
Admin content-item recommendation management endpoints.

Refactoring applied:
- Global @admin_required guard via before_request (R-01).
- @admin_required added explicitly to unlink_match as a belt-and-suspenders
  guard for the DELETE operation (R-19).
"""
from flask import Blueprint, jsonify, request, render_template
from app.core.decorators import admin_required
from app.core.extensions import db
from app.domains.content.models import Content
from app.domains.item.models import Item
from app.domains.relationships import content_items
from app.admin.helpers import paginate_manual, make_rows_response
from sqlalchemy import select, func

bp = Blueprint("api_recommendation", __name__, url_prefix="/admin/recommendations")


@bp.before_request
@admin_required
def require_admin():
    """Ensure all recommendation management endpoints require admin privilege."""
    pass


@bp.route("/stats", methods=["GET"])
def recommendation_stats():
    """Aggregate stats for content-item matches."""
    from app.domains.interaction.models import RecommendationImpression, RecommendationClick
    from datetime import datetime, timedelta, timezone

    total_matches = db.session.execute(
        select(func.count()).select_from(content_items)
    ).scalar() or 0

    linked_contents = db.session.execute(
        select(func.count(func.distinct(content_items.c.content_id)))
    ).scalar() or 0

    linked_items = db.session.execute(
        select(func.count(func.distinct(content_items.c.item_id)))
    ).scalar() or 0

    total_impressions = db.session.execute(
        select(func.count()).select_from(RecommendationImpression)
    ).scalar() or 0
    
    total_clicks = db.session.execute(
        select(func.count()).select_from(RecommendationClick)
    ).scalar() or 0
    
    overall_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0.0
    
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    
    impressions_30d = db.session.execute(
        select(func.count()).select_from(RecommendationImpression)
        .where(RecommendationImpression.created_at >= thirty_days_ago)
    ).scalar() or 0
    
    clicks_30d = db.session.execute(
        select(func.count()).select_from(RecommendationClick)
        .where(RecommendationClick.created_at >= thirty_days_ago)
    ).scalar() or 0

    return jsonify({
        "total_matches":   total_matches,
        "linked_contents": linked_contents,
        "linked_items":    linked_items,
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "overall_ctr": round(overall_ctr, 2),
        "impressions_30d": impressions_30d,
        "clicks_30d": clicks_30d,
    })


def _fetch_matches_page(page, per_page, search, entity_type=None, ctr_range=None):
    """
    Run the paginated matches query and serialize results.
    Returns (total, pages, serialized_list).
    Shared between list_matches (JSON) and matches_rows (HTML partial).
    """
    from app.domains.interaction.models import RecommendationImpression, RecommendationClick

    base_stmt = (
        select(Content.id)
        .join(content_items, Content.id == content_items.c.content_id)
    )
    if search:
        like = f"%{search}%"
        base_stmt = base_stmt.join(Item, Item.id == content_items.c.item_id)
        base_stmt = base_stmt.where(Content.title.ilike(like) | Item.name.ilike(like))
        
    context_id_expr = Content.object_type + '/' + func.cast(Content.object_id, db.String)

    if entity_type:
        base_stmt = base_stmt.where(
            select(RecommendationImpression.id)
            .where(RecommendationImpression.context_id == context_id_expr)
            .where(RecommendationImpression.entity_type == entity_type)
            .exists()
        )

    if ctr_range:
        imp_count = select(func.count(RecommendationImpression.id)).where(RecommendationImpression.context_id == context_id_expr).scalar_subquery()
        click_count = select(func.count(RecommendationClick.id)).where(RecommendationClick.context_id == context_id_expr).scalar_subquery()
        
        ctr_expr = (click_count * 100.0) / func.nullif(imp_count, 0)
        
        if ctr_range == 'high':
            base_stmt = base_stmt.where(ctr_expr > 3.0)
        elif ctr_range == 'medium':
            base_stmt = base_stmt.where(ctr_expr.between(1.0, 3.0))
        elif ctr_range == 'low':
            base_stmt = base_stmt.where(ctr_expr > 0.0).where(ctr_expr < 1.0)
        elif ctr_range == 'zero':
            base_stmt = base_stmt.where(func.coalesce(ctr_expr, 0) == 0).where(imp_count > 0)
    
    base_stmt = base_stmt.group_by(Content.id).order_by(func.max(Content.view_count).desc())

    total_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = db.session.execute(total_stmt).scalar() or 0
    pages = max(1, (total + per_page - 1) // per_page)

    stmt = base_stmt.limit(per_page).offset((page - 1) * per_page)
    content_ids = db.session.execute(stmt).scalars().all()

    if not content_ids:
        return total, pages, []

    detail_stmt = (
        select(Content, Item)
        .select_from(Content)
        .join(content_items, Content.id == content_items.c.content_id)
        .join(Item, Item.id == content_items.c.item_id)
        .where(Content.id.in_(content_ids))
    )
    rows = db.session.execute(detail_stmt).all()

    from app.domains.interaction.models import RecommendationImpression, RecommendationClick
    
    grouped = {}
    for content, item in rows:
        if content.id not in grouped:
            grouped[content.id] = {
                "content_id": content.id,
                "content_title": content.title or f"Content #{content.id}",
                "content_views": content.view_count or 0,
                "object_type": content.object_type,
                "object_id": content.object_id,
                "items": []
            }
        grouped[content.id]["items"].append(item)
    
    serialized = []
    for cid in content_ids:
        if cid in grouped:
            g = grouped[cid]
            
            context_id_val = f"{g['object_type']}/{g['object_id']}"
            
            widget_impressions = db.session.scalar(
                select(func.count(RecommendationImpression.id))
                .where(RecommendationImpression.context_id == context_id_val)
            ) or 0
            
            widget_clicks = db.session.scalar(
                select(func.count(RecommendationClick.id))
                .where(RecommendationClick.context_id == context_id_val)
            ) or 0
            
            widget_ctr = f"{(widget_clicks / widget_impressions * 100):.1f}%" if widget_impressions > 0 else "0.0%"
            
            last_impression = db.session.scalar(
                select(func.max(RecommendationImpression.created_at))
                .where(RecommendationImpression.context_id == context_id_val)
            )
            
            last_active = "Never"
            if last_impression:
                if isinstance(last_impression, str):
                    last_active = last_impression[:16]  # E.g. "2026-06-21 12:34"
                else:
                    last_active = last_impression.strftime("%Y-%m-%d %H:%M")

            serialized.append({
                "content_id": g["content_id"],
                "content_title": g["content_title"],
                "content_views": g["content_views"],
                "widget_impressions": widget_impressions,
                "widget_clicks": widget_clicks,
                "widget_ctr": widget_ctr,
                "last_active": last_active,
                "linked_items_count": len(g["items"]),
                "items": [
                    {
                        "id": i.id,
                        "name": i.name or f"Item #{i.id}",
                        "type": i.item_type,
                        "clicks": i.click_count or 0
                    } for i in g["items"]
                ]
            })
    return total, pages, serialized


@bp.route("/matches", methods=["GET"])
def list_matches():
    """Paginated list of content-item associations for admin inspection."""
    page     = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    search   = request.args.get("search", "").strip()
    entity_type = request.args.get("filter-entity-type", "").strip()
    ctr_range = request.args.get("filter-ctr-range", "").strip()
    
    total, pages, serialized = _fetch_matches_page(page, per_page, search, entity_type, ctr_range)
    return jsonify(paginate_manual(serialized, page, per_page, total))


@bp.route("/matches/rows", methods=["GET"])
def matches_rows():
    """Return server-rendered HTML rows partial for AJAX injection."""
    page     = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    search   = request.args.get("search", "").strip()
    entity_type = request.args.get("filter-entity-type", "").strip()
    ctr_range = request.args.get("filter-ctr-range", "").strip()
    
    total, pages, serialized = _fetch_matches_page(page, per_page, search, entity_type, ctr_range)
    
    display_items = []
    for r in serialized:
        item_ids_str = ", ".join(f"{i['id']}" for i in r['items'])
        display_items.append({
            "id": r["content_id"],
            "content-title": f"{r['content_title']} (#{r['content_id']})",
            "widget-impressions": "{:,}".format(r["widget_impressions"]),
            "widget-ctr": r["widget_ctr"],
            "last-active": r["last_active"],
            "linked-items-count": r["linked_items_count"],
            "linked-items-list": [i['id'] for i in r["items"]]
        })

    html = render_template("admin/components/_rows.html", items=display_items, domain_type="rec")
    return make_rows_response(html, total=total, pages=pages, page=page)


@bp.route("/matches/<int:content_id>/inspect", methods=["GET"])
def inspect_match(content_id):
    """Return server-rendered HTML for the recommendation inspect modal body."""
    from sqlalchemy.orm import selectinload
    content = db.session.execute(
        select(Content).options(selectinload(Content.linked_items)).where(Content.id == content_id)
    ).scalar_one_or_none()
    if not content:
        return "<p class='text-muted'>Content not found.</p>", 404

    from app.admin.tables import get_inspect_table
    
    data = {
        "content id": f"#{content.id}",
        "title": content.title or "—",
        "type": content.object_type,
        "views count": str(content.view_count or 0),
    }
    inspect_table = get_inspect_table("recommendations", data)
    
    from app.domains.interaction.models import ItemClick, RecommendationImpression, RecommendationClick
    from app.domains.item.models import ItemStoreLink, ItemVariant
    
    linked_items_data = []
    referrer_pattern = f"%{content.object_type}/{content.object_id}%" if content.object_id else f"%/{content.id}%"
    context_id_val = f"{content.object_type}/{content.object_id}" if content.object_id else f"article/{content.id}"
    
    # True widget impressions for this context
    widget_impressions = db.session.scalar(
        select(func.count(RecommendationImpression.id))
        .where(RecommendationImpression.context_id == context_id_val)
    ) or 0
    
    unique_users = db.session.scalar(
        select(func.count(func.distinct(RecommendationImpression.user_id)))
        .where(RecommendationImpression.context_id == context_id_val)
        .where(RecommendationImpression.user_id.isnot(None))
    ) or 0
    
    last_impression = db.session.scalar(
        select(func.max(RecommendationImpression.created_at))
        .where(RecommendationImpression.context_id == context_id_val)
    )
    last_active = last_impression.strftime("%Y-%m-%d %H:%M") if last_impression else "Never"
    
    data["widget impressions"] = "{:,}".format(widget_impressions)
    data["unique users reached"] = "{:,}".format(unique_users)
    data["last active"] = last_active

    for i in content.linked_items:
        context_clicks = db.session.scalar(
            select(func.count(ItemClick.id))
            .join(ItemStoreLink, ItemClick.item_store_link_id == ItemStoreLink.id)
            .join(ItemVariant, ItemStoreLink.variant_id == ItemVariant.id)
            .where(ItemVariant.item_id == i.id)
            .where(ItemClick.referrer.ilike(referrer_pattern))
        ) or 0
        
        widget_clicks = db.session.scalar(
            select(func.count(RecommendationClick.id))
            .where(RecommendationClick.context_id == context_id_val)
            .where(RecommendationClick.entity_id == str(i.id))
        ) or 0
        
        widget_ctr = f"{(widget_clicks / widget_impressions * 100):.1f}%" if widget_impressions > 0 else "0.0%"
        affiliate_ctr = f"{(context_clicks / content.view_count * 100):.1f}%" if content.view_count and content.view_count > 0 else "0.0%"
        
        linked_items_data.append({
            "id": i.id,
            "name": i.name or f"Item #{i.id}",
            "type": i.item_type,
            "clicks": f"{widget_clicks} ({widget_ctr} Widget) | {context_clicks} ({affiliate_ctr} Affiliate) | {i.click_count or 0} Total"
        })

    return render_template(
        "admin/components/_inspect.html",
        inspect_table=inspect_table,
        linked_items=linked_items_data,
        inspect_id=content.id
    )

@bp.route("/context-performance", methods=["GET"])
def context_performance():
    from app.domains.interaction.models import RecommendationImpression, RecommendationClick
    
    stmt = (
        select(
            RecommendationImpression.context_id,
            RecommendationImpression.entity_type,
            func.count(RecommendationImpression.id).label("impressions"),
            func.coalesce(
                select(func.count(RecommendationClick.id))
                .where(RecommendationClick.context_id == RecommendationImpression.context_id)
                .scalar_subquery(), 0
            ).label("clicks")
        )
        .group_by(RecommendationImpression.context_id, RecommendationImpression.entity_type)
        .order_by(func.count(RecommendationImpression.id).desc())
        .limit(10)
    )
    
    rows = db.session.execute(stmt).all()
    results = []
    for r in rows:
        ctr = (r.clicks / r.impressions * 100) if r.impressions > 0 else 0
        results.append({
            "context_id": r.context_id,
            "entity_type": r.entity_type,
            "impressions": "{:,}".format(r.impressions),
            "clicks": "{:,}".format(r.clicks),
            "ctr": f"{ctr:.2f}%",
        })
    return jsonify({"data": results})


@bp.route("/entity-performance", methods=["GET"])
def entity_performance():
    from app.domains.interaction.models import RecommendationClick
    from app.domains.item.models import Item
    from app.domains.content.models import Content
    
    stmt = (
        select(
            RecommendationClick.entity_id,
            RecommendationClick.entity_type,
            func.count(RecommendationClick.id).label("clicks")
        )
        .group_by(RecommendationClick.entity_id, RecommendationClick.entity_type)
        .order_by(func.count(RecommendationClick.id).desc())
        .limit(10)
    )
    
    rows = db.session.execute(stmt).all()
    results = []
    for r in rows:
        name = f"Entity #{r.entity_id}"
        if str(r.entity_id).isdigit():
            if r.entity_type == "related_content":
                content = db.session.get(Content, int(r.entity_id))
                if content: name = content.title
            else:
                item = db.session.get(Item, int(r.entity_id))
                if item: name = item.name
                
        results.append({
            "entity_id": r.entity_id,
            "entity_name": name,
            "entity_type": r.entity_type,
            "clicks": "{:,}".format(r.clicks),
        })
    return jsonify({"data": results})


@bp.route("/health", methods=["GET"])
def system_health():
    from app.domains.interaction.models import RecommendationImpression, RecommendationClick
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    
    last_impression = db.session.scalar(
        select(func.max(RecommendationImpression.created_at))
    )
    
    signals = []
    
    if last_impression:
        # Avoid offset-naive and offset-aware subtraction issues
        if last_impression.tzinfo is None:
            last_impression = last_impression.replace(tzinfo=timezone.utc)
        hours_since = (now - last_impression).total_seconds() / 3600
        if hours_since > 48:
            signals.append({
                "level": "critical", 
                "message": f"No impressions recorded in the last {int(hours_since)} hours."
            })
    else:
        signals.append({
            "level": "critical", 
            "message": "No impressions ever recorded."
        })
        
    seven_days_ago = now - timedelta(days=7)
    imp_7d = db.session.scalar(
        select(func.count(RecommendationImpression.id))
        .where(RecommendationImpression.created_at >= seven_days_ago)
    ) or 0
    
    click_7d = db.session.scalar(
        select(func.count(RecommendationClick.id))
        .where(RecommendationClick.created_at >= seven_days_ago)
    ) or 0
    
    if imp_7d > 100:
        ctr_7d = (click_7d / imp_7d) * 100
        if ctr_7d < 0.5:
            signals.append({
                "level": "warning", 
                "message": f"7-day overall CTR is dangerously low ({ctr_7d:.2f}%)."
            })
            
    if not signals:
        signals.append({
            "level": "success",
            "message": f"Recommendation system is healthy. {imp_7d} impressions in last 7 days."
        })
        status = "success"
    else:
        status = "critical" if any(s["level"] == "critical" for s in signals) else "warning"
        
    return jsonify({
        "status": status,
        "signals": signals
    })

@bp.route("/trend", methods=["GET"])
def recommendation_trend():
    from app.domains.interaction.models import RecommendationImpression, RecommendationClick
    from datetime import datetime, timedelta, timezone

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    
    imp_stmt = (
        select(
            func.date(RecommendationImpression.created_at).label("day"),
            func.count(RecommendationImpression.id).label("count")
        )
        .where(RecommendationImpression.created_at >= thirty_days_ago)
        .group_by("day")
    )
    
    click_stmt = (
        select(
            func.date(RecommendationClick.created_at).label("day"),
            func.count(RecommendationClick.id).label("count")
        )
        .where(RecommendationClick.created_at >= thirty_days_ago)
        .group_by("day")
    )
    
    imp_rows = db.session.execute(imp_stmt).all()
    click_rows = db.session.execute(click_stmt).all()
    
    data = {}
    for i in range(30, -1, -1):
        day_str = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        data[day_str] = {"impressions": 0, "clicks": 0}
        
    for r in imp_rows:
        day_str = str(r.day)
        if day_str in data:
            data[day_str]["impressions"] = r.count
            
    for r in click_rows:
        day_str = str(r.day)
        if day_str in data:
            data[day_str]["clicks"] = r.count
            
    labels = list(data.keys())
    impressions = [data[d]["impressions"] for d in labels]
    clicks = [data[d]["clicks"] for d in labels]
    
    return jsonify({
        "labels": [d[5:] for d in labels],
        "impressions": impressions,
        "clicks": clicks
    })

@bp.route("/slot-analysis", methods=["GET"])
def slot_analysis():
    from app.domains.interaction.models import RecommendationImpression, RecommendationClick
    
    clicks = db.session.execute(
        select(RecommendationClick)
        .order_by(RecommendationClick.created_at.desc())
        .limit(1000)
    ).scalars().all()
    
    impressions = db.session.execute(
        select(RecommendationImpression)
        .order_by(RecommendationImpression.created_at.desc())
        .limit(3000)
    ).scalars().all()
    
    imp_dict = {}
    for imp in impressions:
        key = (imp.context_id, imp.user_id) if imp.user_id else imp.context_id
        if key not in imp_dict:
            imp_dict[key] = []
        imp_dict[key].append(imp)
        
    slot_counts = {}
    for c in clicks:
        key = (c.context_id, c.user_id) if c.user_id else c.context_id
        imps = imp_dict.get(key, [])
        valid_imps = [i for i in imps if i.created_at <= c.created_at]
        if valid_imps:
            best_imp = valid_imps[0]
            try:
                entity_ids = best_imp.entity_ids
                if isinstance(entity_ids, str):
                    import json
                    entity_ids = json.loads(entity_ids)
                if not entity_ids:
                    continue
                str_ids = [str(eid) for eid in entity_ids]
                if str(c.entity_id) in str_ids:
                    idx = str_ids.index(str(c.entity_id))
                    slot_counts[idx] = slot_counts.get(idx, 0) + 1
            except:
                pass
                
    max_slots = max(slot_counts.keys()) if slot_counts else 0
    limit_slots = min(10, max_slots + 1) if max_slots > 0 else 5
    
    labels = [f"Slot {i+1}" for i in range(limit_slots)]
    data = [slot_counts.get(i, 0) for i in range(limit_slots)]
    
    return jsonify({"labels": labels, "data": data})

@bp.route("/user_interests/<int:user_id>/inspect", methods=["GET"])
def inspect_user_interests(user_id):
    from app.domains.user.models import User
    from app.domains.recommendation.models import UserInterest, UserEntityInterest
    from app.domains.taxonomy.models import Brand, Category, Topic
    
    user = db.session.get(User, user_id)
    if not user:
        return "<p class='text-muted'>User not found.</p>", 404
        
    scores = db.session.execute(
        select(
            UserEntityInterest.brand_id,
            UserEntityInterest.category_id,
            UserEntityInterest.topic_id,
            func.sum(UserEntityInterest.score).label("total_score")
        )
        .join(UserInterest, UserEntityInterest.user_interest_id == UserInterest.id)
        .where(UserInterest.user_id == user_id)
        .group_by(UserEntityInterest.brand_id, UserEntityInterest.category_id, UserEntityInterest.topic_id)
        .order_by(func.sum(UserEntityInterest.score).desc())
        .limit(5)
    ).all()
    
    data = {}
    
    for i, row in enumerate(scores):
        name = "Unknown"
        if row.brand_id:
            brand = db.session.get(Brand, row.brand_id)
            name = f"Brand: {brand.name}" if brand else f"Brand #{row.brand_id}"
        elif row.category_id:
            category = db.session.get(Category, row.category_id)
            name = f"Category: {category.name}" if category else f"Category #{row.category_id}"
        elif row.topic_id:
            topic = db.session.get(Topic, row.topic_id)
            name = f"Topic: {topic.name}" if topic else f"Topic #{row.topic_id}"
            
        data[f"affinity {i+1}"] = {
            "value": f"<b>{name}</b> - Score: {round(row.total_score, 3)}",
            "is_custom": True
        }
        
    for i in range(len(scores), 5):
        data[f"affinity {i+1}"] = "—"
        
    from app.admin.tables import get_inspect_table
    inspect_table = get_inspect_table("user_interests", data)
    
    return render_template(
        "admin/components/_inspect.html",
        inspect_table=inspect_table,
        actions=[]
    )


@bp.route("/matches/<int:content_id>/<int:item_id>", methods=["DELETE"])
def unlink_match(content_id, item_id):
    """Remove a content-item association."""
    db.session.execute(
        content_items.delete().where(
            content_items.c.content_id == content_id,
            content_items.c.item_id == item_id,
        )
    )
    db.session.commit()
    return jsonify({"success": True, "message": "Association removed."})
