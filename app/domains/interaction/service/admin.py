from sqlalchemy import select, func, or_, case
from app.core.extensions import db
from app.domains.interaction.models import Comment, Reaction, View, Save, Share, ItemClick
from app.domains.user.models import User
from app.domains.content.models import Content
from app.domains.item.models import Item, ItemStoreLink, ItemVariant, Store
import math
from datetime import date, datetime

def _load_interaction_context(items):
    user_ids     = {c.user_id for c in items if getattr(c, 'user_id', None)}
    content_ids  = {c.target_id for c in items if getattr(c, 'target_type', None) == "content"}
    item_ids     = {c.target_id for c in items if getattr(c, 'target_type', None) == "item"}
    users, content_titles, item_names = {}, {}, {}
    if user_ids:
        rows = db.session.execute(select(User.id, User.name, User.email).where(User.id.in_(user_ids))).mappings().all()
        users = {r["id"]: r for r in rows}
    if content_ids:
        rows = db.session.execute(select(Content.id, Content.title).where(Content.id.in_(content_ids))).mappings().all()
        content_titles = {r["id"]: r["title"] for r in rows}
    if item_ids:
        rows = db.session.execute(select(Item.id, Item.name).where(Item.id.in_(item_ids))).mappings().all()
        item_names = {r["id"]: r["name"] for r in rows}
    return users, content_titles, item_names

def _load_target_titles(items, type_attr="target_type", id_attr="target_id"):
    content_ids = {getattr(obj, id_attr) for obj in items if getattr(obj, type_attr) == "content"}
    item_ids    = {getattr(obj, id_attr) for obj in items if getattr(obj, type_attr) == "item"}
    content_titles, item_names = {}, {}
    if content_ids:
        rows = db.session.execute(
            select(Content.id, Content.title).where(Content.id.in_(content_ids))
        ).mappings().all()
        content_titles = {r["id"]: r["title"] for r in rows}
    if item_ids:
        rows = db.session.execute(
            select(Item.id, Item.name).where(Item.id.in_(item_ids))
        ).mappings().all()
        item_names = {r["id"]: r["name"] for r in rows}
    return content_titles, item_names

def _serialize_comment(c, users, content_titles, item_names):
    user = users.get(c.user_id)
    target_title = (
        content_titles.get(c.target_id)
        if c.target_type == "content"
        else item_names.get(c.target_id)
    )
    return {
        "id":           c.id,
        "content":      c.content,
        "preview":      c.content[:120] + ("…" if len(c.content) > 120 else ""),
        "user_id":      c.user_id,
        "user_name":    user["name"] if user else f"User #{c.user_id}",
        "user_email":   user["email"] if user else None,
        "parent_id":    c.parent_id,
        "sentiment":    c.sentiment or "neutral",
        "confidence":   c.confidence,
        "target_type":  c.target_type,
        "target_id":    c.target_id,
        "like_count":   c.like_count,
        "dislike_count": c.dislike_count,
        "replies_count": c.replies_count,
        "replies":      c.replies,
        "target_title": target_title or f"{c.target_type.capitalize()} #{c.target_id}",
        "created_at":   c.created_at.isoformat() if c.created_at else None,
    }

def get_admin_comments_page(page, per_page, sentiment, target_type, search, user_search, start_date, end_date):
    stmt = select(Comment).order_by(Comment.id.desc())
    if user_search:
        stmt = stmt.join(User, Comment.user_id == User.id)
    if sentiment:
        stmt = stmt.where(Comment.sentiment == sentiment)
    if target_type:
        stmt = stmt.where(Comment.target_type == target_type)
    if search:
        stmt = stmt.where(Comment.content.ilike(f"%{search}%"))
    if user_search:
        stmt = stmt.where(
            or_(User.name.ilike(f"%{user_search}%"), User.email.ilike(f"%{user_search}%"))
        )
    if start_date:
        try:
            stmt = stmt.where(Comment.created_at >= datetime.combine(date.fromisoformat(start_date), datetime.min.time()))
        except ValueError:
            pass
    if end_date:
        try:
            stmt = stmt.where(Comment.created_at <= datetime.combine(date.fromisoformat(end_date), datetime.max.time()))
        except ValueError:
            pass

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    users, content_titles, item_names = _load_interaction_context(pagination.items)

    serialized = [_serialize_comment(c, users, content_titles, item_names) for c in pagination.items]
    return pagination, serialized

def delete_admin_comment(id):
    comment = db.session.get(Comment, id)
    if not comment:
        return False
    db.session.delete(comment)
    db.session.commit()
    return True

def flag_admin_comment_as_spam(id):
    comment = db.session.get(Comment, id)
    if not comment:
        return False
    comment.sentiment = "spam"
    db.session.commit()
    return True

def build_admin_comment_inspect_data(id):
    from app.domains.interaction.service.inspect import get_comment_inspect_metrics
    metrics = get_comment_inspect_metrics(id)
    if not metrics:
        return None
        
    comment = metrics["comment"]
    total_user_comments = metrics["total_user_comments"]
    target_sentiments = metrics["target_sentiments"]
    recent_reactions = metrics["recent_reactions"]
    
    
    target_title = comment.target.title if comment.target_type == 'content' and comment.target else (comment.target.name if comment.target else f"{comment.target_type.capitalize()} #{comment.target_id}")
    
    parent_context = "—"
    if comment.parent:
        parent_context = comment.parent.content[:60] + ("…" if len(comment.parent.content) > 60 else "")

    latest_replies = "—"
    if comment.replies:
        sorted_replies = sorted(comment.replies, key=lambda r: r.created_at, reverse=True)
        latest_replies = [{"label": f"• {r.content[:40]}..."} for r in sorted_replies[:3]]

    total_target_comments = sum(count for _, count in target_sentiments)
    sentiment_dist = []
    for sentiment, count in target_sentiments:
        pct = (count / total_target_comments * 100) if total_target_comments > 0 else 0
        s_label = sentiment.title() if sentiment else 'Neutral'
        sentiment_dist.append({"label": s_label, "count": f"{count} ({pct:.1f}%)"})
    
    reactions_html = "—"
    if recent_reactions:
        reactions_html = [{"label": r.user.name if r.user else 'User', "detail": r.type.title()} for r in recent_reactions]

    data = {
        "id": f"#{comment.id}",
        "comment": comment.content,
        "sentiment": comment.sentiment or "neutral",
        "confidence": str(round(comment.confidence, 2)) if comment.confidence else "—",
        "likes": "{:,}".format(comment.like_count),
        "dislikes": "{:,}".format(comment.dislike_count),
        "shares": "{:,}".format(comment.share_count),
        "replies count": str(comment.replies_count),
        "recent reactions": {"value": reactions_html, "is_list": True} if reactions_html != "—" else "—",
        "user id": str(comment.user_id),
        "user name": comment.user.name if comment.user else "—",
        "user email": comment.user.email if comment.user else "—",
        "total comments": str(total_user_comments),
        "parent context": parent_context,
        "latest replies": {"value": latest_replies, "is_list": True} if latest_replies != "—" else "—",
        "target type": comment.target_type,
        "target title": target_title,
        "date": comment.created_at.isoformat()[:10] if comment.created_at else "—",
        "target comments": str(total_target_comments),
        "sentiment distribution": {"value": sentiment_dist, "is_list": True} if sentiment_dist else "—"
    }
    actions = [
        {
            "label": "Already Flagged" if comment.sentiment == 'spam' else "Flag as Spam",
            "action_type": "toggle-active",
            "icon": "🚩",
            "disabled": True if comment.sentiment == 'spam' else False,
            "attrs": {"data-action": "flag-comment", "data-id": comment.id}
        },
        {
            "label": "Delete Comment",
            "action_type": "delete",
            "icon": "🗑",
            "extra_class": "inspect-delete-btn",
            "attrs": {"data-action": "delete-comment", "data-id": comment.id}
        }
    ]

    return {
        "raw_data": data,
        "actions": actions,
        "inspect_id": comment.id
    }

def get_admin_reactions_page(page, per_page, reaction_type, target, user_search):
    stmt = select(Reaction).order_by(Reaction.id.desc())
    if reaction_type:
        stmt = stmt.where(Reaction.type == reaction_type)

    stmt = stmt.outerjoin(Content, (Reaction.target_id == Content.id) & (Reaction.target_type == "content"))
    stmt = stmt.outerjoin(Item, (Reaction.target_id == Item.id) & (Reaction.target_type == "item"))
    stmt = stmt.join(User, Reaction.user_id == User.id)

    if target:
        stmt = stmt.where(
            or_(
                Content.title.ilike(f"%{target}%"),
                Item.name.ilike(f"%{target}%")
            )
        )
    if user_search:
        stmt = stmt.where(
            or_(
                User.name.ilike(f"%{user_search}%"),
                User.email.ilike(f"%{user_search}%")
            )
        )

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    users, content_titles, item_names = _load_interaction_context(pagination.items)
    
    comment_ids = {r.target_id for r in pagination.items if r.target_type == "comment"}
    comment_previews = {}
    if comment_ids:
        rows = db.session.execute(
            select(Comment.id, Comment.content).where(Comment.id.in_(comment_ids))
        ).mappings().all()
        comment_previews = {r["id"]: r["content"][:60] + ("…" if len(r["content"]) > 60 else "") for r in rows}

    serialized = []
    for r in pagination.items:
        user = users.get(r.user_id)
        if r.target_type == "content":
            target_title = content_titles.get(r.target_id)
            icon = "📄 Content"
        elif r.target_type == "item":
            target_title = item_names.get(r.target_id)
            icon = "📦 Item"
        else:
            target_title = comment_previews.get(r.target_id)
            icon = "💬 Comment"

        serialized.append({
            "id":          r.id,
            "type":        r.type,
            "user_id":     r.user_id,
            "username":   user["name"] if user else f"User #{r.user_id}",
            "user_email":  user["email"] if user else None,
            "target_type": r.target_type,
            "target_icon": icon,
            "target_id":   r.target_id,
            "target_title": target_title or f"{r.target_type.capitalize()} #{r.target_id}",
            "created_at":  r.created_at.isoformat() if r.created_at else None,
        })
    return pagination, serialized

def get_admin_views_page(page, per_page, target, start_date, end_date):
    stmt = (
        select(
            View.target_type,
            View.target_id,
            func.count(View.id).label("view_count"),
            func.sum(case((View.user_id.isnot(None), 1), else_=0)).label("auth_views"),
            func.sum(case((View.user_id.is_(None), 1), else_=0)).label("anon_views"),
            func.max(View.created_at).label("latest_view")
        )
        .select_from(View)
    )

    stmt = stmt.outerjoin(Content, (View.target_id == Content.id) & (View.target_type == "content"))
    stmt = stmt.outerjoin(Item, (View.target_id == Item.id) & (View.target_type == "item"))

    if target:
        stmt = stmt.where(
            or_(
                Content.title.ilike(f"%{target}%"),
                Item.name.ilike(f"%{target}%")
            )
        )

    if start_date:
        try:
            stmt = stmt.where(View.created_at >= datetime.combine(date.fromisoformat(start_date), datetime.min.time()))
        except ValueError:
            pass
    if end_date:
        try:
            stmt = stmt.where(View.created_at <= datetime.combine(date.fromisoformat(end_date), datetime.max.time()))
        except ValueError:
            pass

    stmt = stmt.group_by(View.target_type, View.target_id).order_by(func.max(View.created_at).desc())

    total = db.session.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
    paginated_stmt = stmt.limit(per_page).offset((page - 1) * per_page)
    items = db.session.execute(paginated_stmt).all()

    content_titles, item_names = _load_target_titles(items)
    pages = math.ceil(total / per_page) if per_page > 0 else 1

    serialized = []
    for v in items:
        target_title = (
            content_titles.get(v.target_id)
            if v.target_type == "content"
            else item_names.get(v.target_id)
        )
        serialized.append({
            "id": f"{v.target_type}-{v.target_id}",
            "target_type": v.target_type,
            "target_id": v.target_id,
            "target_title": target_title or f"{v.target_type.capitalize()} #{v.target_id}",
            "view_count": v.view_count,
            "auth_views": v.auth_views or 0,
            "anon_views": v.anon_views or 0,
            "latest_view": v.latest_view.isoformat() if v.latest_view else None,
            "created_at": v.latest_view.isoformat() if v.latest_view else None
        })
    return {"items": serialized, "page": page, "pages": pages, "total": total, "per_page": per_page}

def get_admin_clicks_page(page, per_page, target, destination):
    stmt = (
        select(
            ItemStoreLink.id.label("link_id"),
            ItemStoreLink.affiliate_url,
            Store.name.label("store_name"),
            Item.id.label("item_id"),
            Item.name.label("item_name"),
            func.count(ItemClick.id).label("click_count"),
            func.max(ItemClick.created_at).label("latest_click")
        )
        .select_from(ItemClick)
        .join(ItemStoreLink, ItemClick.item_store_link_id == ItemStoreLink.id)
        .join(Store, ItemStoreLink.store_id == Store.id)
        .join(ItemVariant, ItemStoreLink.variant_id == ItemVariant.id)
        .join(Item, ItemVariant.item_id == Item.id)
    )

    if target:
        stmt = stmt.where(or_(Item.name.ilike(f"%{target}%"), Store.name.ilike(f"%{target}%")))
    if destination:
        if destination.isdigit():
            stmt = stmt.where(Store.id == int(destination))
        else:
            stmt = stmt.where(Store.name.ilike(f"%{destination}%"))

    stmt = stmt.group_by(
        ItemStoreLink.id,
        ItemStoreLink.affiliate_url,
        Store.name,
        Item.id,
        Item.name
    ).order_by(func.max(ItemClick.created_at).desc())

    total = db.session.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
    paginated_stmt = stmt.limit(per_page).offset((page - 1) * per_page)
    items = db.session.execute(paginated_stmt).all()

    pages = math.ceil(total / per_page) if per_page > 0 else 1

    serialized = []
    for row in items:
        serialized.append({
            "link_id": row.link_id,
            "affiliate_url": row.affiliate_url,
            "store_name": row.store_name,
            "item_id": row.item_id,
            "item_name": row.item_name,
            "click_count": row.click_count,
            "latest_click": row.latest_click.isoformat() if row.latest_click else None,
            "created_at": row.latest_click.isoformat() if row.latest_click else None
        })

    return {"items": serialized, "page": page, "pages": pages, "total": total, "per_page": per_page}

def get_admin_saves_page(page, per_page, target, user_search):
    stmt = select(Save).order_by(Save.id.desc())

    stmt = stmt.outerjoin(Content, (Save.target_id == Content.id) & (Save.target_type == "content"))
    stmt = stmt.outerjoin(Item, (Save.target_id == Item.id) & (Save.target_type == "item"))
    stmt = stmt.join(User, Save.user_id == User.id)

    if target:
        stmt = stmt.where(
            or_(
                Content.title.ilike(f"%{target}%"),
                Item.name.ilike(f"%{target}%")
            )
        )
    if user_search:
        stmt = stmt.where(
            or_(
                User.name.ilike(f"%{user_search}%"),
                User.email.ilike(f"%{user_search}%")
            )
        )

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    users, content_titles, item_names = _load_interaction_context(pagination.items)

    serialized = []
    for s in pagination.items:
        user = users.get(s.user_id)
        target_title = (
            content_titles.get(s.target_id)
            if s.target_type == "content"
            else item_names.get(s.target_id)
        )
        serialized.append({
            "id": s.id,
            "user_id": s.user_id,
            "user_name": user["name"] if user else f"User #{s.user_id}",
            "user_email": user["email"] if user else None,
            "target_type": s.target_type,
            "target_id": s.target_id,
            "target_title": target_title or f"{s.target_type.capitalize()} #{s.target_id}",
            "created_at": s.created_at.isoformat() if s.created_at else None
        })

    return pagination, serialized

def get_admin_shares_page(page, per_page, target, user_search):
    stmt = select(Share).order_by(Share.id.desc())

    stmt = stmt.outerjoin(Content, (Share.target_id == Content.id) & (Share.target_type == "content"))
    stmt = stmt.outerjoin(Item, (Share.target_id == Item.id) & (Share.target_type == "item"))
    stmt = stmt.join(User, Share.user_id == User.id)

    if target:
        stmt = stmt.where(
            or_(
                Content.title.ilike(f"%{target}%"),
                Item.name.ilike(f"%{target}%")
            )
        )
    if user_search:
        stmt = stmt.where(
            or_(
                User.name.ilike(f"%{user_search}%"),
                User.email.ilike(f"%{user_search}%")
            )
        )

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    users, content_titles, item_names = _load_interaction_context(pagination.items)

    serialized = []
    for s in pagination.items:
        user = users.get(s.user_id)
        target_title = (
            content_titles.get(s.target_id)
            if s.target_type == "content"
            else item_names.get(s.target_id)
        )
        serialized.append({
            "id": s.id,
            "user_id": s.user_id,
            "user_name": user["name"] if user else f"User #{s.user_id}",
            "user_email": user["email"] if user else None,
            "target_type": s.target_type,
            "target_id": s.target_id,
            "target_title": target_title or f"{s.target_type.capitalize()} #{s.target_id}",
            "channel": s.channel or "—",
            "created_at": s.created_at.isoformat() if s.created_at else None
        })

    return pagination, serialized
