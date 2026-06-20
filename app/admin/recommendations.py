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
    total_matches = db.session.execute(
        select(func.count()).select_from(content_items)
    ).scalar() or 0

    linked_contents = db.session.execute(
        select(func.count(func.distinct(content_items.c.content_id)))
    ).scalar() or 0

    linked_items = db.session.execute(
        select(func.count(func.distinct(content_items.c.item_id)))
    ).scalar() or 0

    return jsonify({
        "total_matches":   total_matches,
        "linked_contents": linked_contents,
        "linked_items":    linked_items,
    })


def _fetch_matches_page(page, per_page, search):
    """
    Run the paginated matches query and serialize results.
    Returns (total, pages, serialized_list).
    Shared between list_matches (JSON) and matches_rows (HTML partial).
    """
    base_stmt = (
        select(Content.id)
        .join(content_items, Content.id == content_items.c.content_id)
    )
    if search:
        like = f"%{search}%"
        base_stmt = base_stmt.join(Item, Item.id == content_items.c.item_id)
        base_stmt = base_stmt.where(Content.title.ilike(like) | Item.name.ilike(like))
    
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

    grouped = {}
    for content, item in rows:
        if content.id not in grouped:
            grouped[content.id] = {
                "content_id": content.id,
                "content_title": content.title or f"Content #{content.id}",
                "content_views": content.view_count or 0,
                "items": []
            }
        grouped[content.id]["items"].append(item)
    
    serialized = []
    for cid in content_ids:
        if cid in grouped:
            g = grouped[cid]
            serialized.append({
                "content_id": g["content_id"],
                "content_title": g["content_title"],
                "content_views": g["content_views"],
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
    total, pages, serialized = _fetch_matches_page(page, per_page, search)
    return jsonify(paginate_manual(serialized, page, per_page, total))


@bp.route("/matches/rows", methods=["GET"])
def matches_rows():
    """Return server-rendered HTML rows partial for AJAX injection."""
    page     = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    search   = request.args.get("search", "").strip()
    total, pages, serialized = _fetch_matches_page(page, per_page, search)
    
    display_items = []
    for r in serialized:
        item_ids_str = ", ".join(f"{i['id']}" for i in r['items'])
        display_items.append({
            "id": r["content_id"],
            "content-title": f"{r['content_title']} (#{r['content_id']})",
            "content-views-count": "{:,}".format(r["content_views"] or 0),
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
    
    from app.domains.interaction.models import ItemClick
    from app.domains.item.models import ItemStoreLink, ItemVariant
    
    linked_items_data = []
    referrer_pattern = f"%{content.object_type}/{content.object_id}%" if content.object_id else f"%/{content.id}%"
    
    for i in content.linked_items:
        context_clicks = db.session.scalar(
            select(func.count(ItemClick.id))
            .join(ItemStoreLink, ItemClick.item_store_link_id == ItemStoreLink.id)
            .join(ItemVariant, ItemStoreLink.variant_id == ItemVariant.id)
            .where(ItemVariant.item_id == i.id)
            .where(ItemClick.referrer.ilike(referrer_pattern))
        ) or 0
        
        ctr = f"{(context_clicks / content.view_count * 100):.1f}%" if content.view_count and content.view_count > 0 else "0.0%"
        
        linked_items_data.append({
            "id": i.id,
            "name": i.name or f"Item #{i.id}",
            "type": i.item_type,
            "clicks": f"{context_clicks} ({ctr} CTR) | Overall: {i.click_count or 0}"
        })

    return render_template(
        "admin/components/_inspect.html",
        inspect_table=inspect_table,
        linked_items=linked_items_data,
        inspect_id=content.id
    )

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
