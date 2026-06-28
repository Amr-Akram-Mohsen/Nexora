from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, abort, current_app
from flask_login import current_user, login_required
from app.core.extensions import limiter, db, csrf
from app.shared.constants.core import TargetType
from app.shared.parsing import parse_target_type, parse_interaction_type
from app.shared.request import get_client_ip
from app.core.context import get_newsletter_context
from app.application.interaction.newsletter import subscribe_workflow, confirm_subscription_workflow, unsubscribe_workflow
from app.application.interaction.handle_interaction import handle_interaction_workflow
from app.application.interaction.item_click import record_item_click_workflow
from app.domains.interaction.constants import INTERACTION_TYPE
from app.domains.interaction.service import check_user_reaction, check_user_save, get_saved_items
from app.domains.content.service import get_content_by_id
from app.domains.item.service import get_item_by_id
from app.application.interaction.tracking import track_view_workflow, track_impression_workflow, track_click_workflow
from app.shared.utils.logging import log_route_start, log_route_success
import logging

logger = logging.getLogger(__name__)

bp = Blueprint("interaction", __name__)


def _newsletter_component_context(email=None):
    placement = request.form.get("newsletter_placement") or "default"
    if placement not in {"default", "home", "article", "landing", "profile"}:
        placement = "default"
    return {
        **get_newsletter_context(email=email),
        "newsletter_title": request.form.get("newsletter_title") or None,
        "newsletter_description": request.form.get("newsletter_description") or None,
        "newsletter_placement": placement,
    }


def _newsletter_response(success, message, email=None, status_code=200):
    context = _newsletter_component_context(email=email)
    payload = {
        "success": success,
        "message": message if success else None,
        "error": None if success else message,
        "state": {
            "status": context.get("newsletter_status"),
            "is_subscribed": bool(context.get("is_subscribed")),
            "is_pending": bool(context.get("is_pending")),
            "email": context.get("newsletter_email"),
        },
    }
    if success:
        payload["html"] = render_template("partials/newsletter.html", **context)
    return jsonify(payload), status_code


@bp.route('/subscribe', methods=['POST'])
@limiter.limit("5 per minute")
def subscribe():
    email = current_user.email if current_user.is_authenticated else request.form.get('email')
    user_id = current_user.id if current_user.is_authenticated else None

    success, message = subscribe_workflow(email, user_id)
    return _newsletter_response(success, message, email=email, status_code=400 if not success else 200)

@bp.route('/confirm-subscription/<token>')
def confirm_subscription(token):
    if confirm_subscription_workflow(token):
        flash("Your subscription has been confirmed.", "success")
    else:
        flash("Invalid or expired confirmation link.", "error")
    return redirect(url_for('system.newsletter'))

@bp.route('/unsubscribe-auth', methods=['POST'])
@login_required
def unsubscribe_auth():
    success, message = unsubscribe_workflow(user=current_user)
    return _newsletter_response(
        success,
        message,
        email=current_user.email,
        status_code=400 if not success else 200,
    )

@bp.route('/unsubscribe/<token>')
def unsubscribe_token(token):
    if unsubscribe_workflow(token=token):
        flash("You have been unsubscribed successfully.", "success")
    else:
        flash("Invalid unsubscribe link.", "error")
    return redirect(url_for('system.newsletter'))

@bp.route("/check-react-batch")
@login_required
def check_react_batch():
    target_types = request.args.getlist("type")
    target_ids = request.args.getlist("id")
    if len(target_types) != len(target_ids):
        abort(400, "Mismatched parameters")
    
    result = {}
    for t_str, id_str in zip(target_types, target_ids):
        try:
            target_type = "comment" if t_str == "comment" else parse_target_type(t_str)
            target_id = int(id_str)
        except (ValueError, TypeError):
            continue
        
        reaction = check_user_reaction(current_user.id, target_type, target_id)
        if reaction:
            result[f"{t_str}:{id_str}"] = reaction.type
    return jsonify(result)

@bp.route("/check-save-batch")
@login_required
def check_save_batch():
    target_types = request.args.getlist("type")
    target_ids = request.args.getlist("id")
    if len(target_types) != len(target_ids):
        abort(400, "Mismatched parameters")
    
    result = {}
    for t_str, id_str in zip(target_types, target_ids):
        try:
            target_type = parse_target_type(t_str)
            target_id = int(id_str)
        except (ValueError, TypeError):
            continue
        
        if check_user_save(current_user.id, target_type, target_id):
            result[f"{t_str}:{id_str}"] = True
    return jsonify(result)

@bp.route("/get-comments")
def get_comments():
    try:
        target_type = parse_target_type(request.args.get("type"))
        target_id = int(request.args.get("id"))
    except (ValueError, TypeError):
        abort(400, "Invalid parameters")
    
    parent_id = request.args.get("parent_id", type=int)
    
    from app.domains.interaction.service import get_comments_for_target
    comments = get_comments_for_target(target_type, target_id, parent_id)
    
    comments_html = "".join(
        render_template(
            'components/interactions/comment-card.html',
            comment=c,
            is_reply=parent_id is not None
        ) for c in comments
    )
    
    return comments_html

@bp.route("/item-click/<int:link_id>", methods=["POST"])
def item_click(link_id):
    user = current_user if current_user.is_authenticated else None
    ip_address = request.remote_addr if not (user and user.is_authenticated) else None
    
    redirect_url = record_item_click_workflow(
        link_id,
        user,
        ip_address,
        request.headers.get("User-Agent"),
        request.referrer,
        request.headers.get("CF-IPCountry")
    )
    
    if not redirect_url:
        abort(404)
        
    return jsonify({"redirect_url": redirect_url})

@bp.route("/view", methods=["POST"])
def add_view():
    try:
        target_type = parse_target_type(request.form.get("type"))
        target_id = int(request.form.get("id"))
    except (ValueError, TypeError):
        abort(400, "Invalid parameters")
        
    user = current_user if current_user.is_authenticated else None
    ip = None if user else get_client_ip()
    
    target = None
    if target_type == TargetType.ARTICLE:
        target = get_content_by_id(target_id)
    else:
        target = get_item_by_id(target_id, load="minimal")
        
    if not target:
        abort(404)
        
    result = track_view_workflow(target_id, target_type, user, ip)
    return jsonify(result)

@bp.route("/handle-interaction", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def handle_interaction():
    try:
        target_type = parse_target_type(request.form.get("type"))
        target_id = int(request.form.get("id"))
        interaction_type = parse_interaction_type(request.form.get("interaction_type"))

        log_route_start(
            logger, "/handle-interaction",
            type=str(target_type),
            id=target_id,
            interaction=str(interaction_type),
        )

        result = handle_interaction_workflow(
            user=current_user,
            target_type=target_type,
            target_id=target_id,
            interaction_type=interaction_type,
            reaction_type=request.form.get("reaction"),
            comment_content=request.form.get("comment", "").strip(),
            comment_id=request.form.get('comment_id', type=int),
            collection_name=request.form.get("collection_name")
        )

        if not result.get("success"):
            return jsonify(result), 400

        if interaction_type == INTERACTION_TYPE.COMMENT and "comment_data" in result:
            result["comment"] = render_template(
                'components/interactions/comment-card.html',
                comment=result["comment_data"],
                is_reply=request.form.get('comment_id', type=int) is not None
            )
            del result["comment_data"]

        log_route_success(logger, "/handle-interaction")
        return jsonify(result)
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Invalid interaction request"}), 400
    except Exception:
        current_app.logger.exception("Interaction failed")
        return jsonify({"success": False, "error": "Interaction failed"}), 500

@bp.route('/saved')
@login_required
def saved_items():
    from app.application.interaction.get_saved import (
        get_saved_articles_workflow,
        get_saved_products_workflow,
    )

    log_route_start(logger, "/saved", user_id=current_user.id)
    
    saved_articles = get_saved_articles_workflow(current_user.id)
    saved_items = get_saved_products_workflow(current_user.id)
    
    # Extract collections
    collections = set()
    for item in saved_articles + saved_items:
        if item.get("collection_name"):
            collections.add(item["collection_name"])
    
    collections = sorted(list(collections))

    log_route_success(
        logger, "/saved",
        items=(len(saved_articles) + len(saved_items)),
        template="saved-items.html",
    )
    return render_template(
        'saved-items.html',
        saved_articles=saved_articles,
        saved_items=saved_items,
        collections=collections
    )


@bp.route("/track/impression", methods=["POST"])
@csrf.exempt
def track_impression():
    data = request.get_json() or {}
    entity_type = data.get("entity_type")
    context_id = data.get("context_id")
    entity_ids = data.get("entity_ids", [])
    
    if not entity_type or not entity_ids:
        return jsonify({"success": False, "error": "Missing parameters"}), 400
        
    user_id = current_user.id if current_user.is_authenticated else None
    
    success = track_impression_workflow(entity_type, entity_ids, context_id, user_id)
    
    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Failed to track impression"}), 500


@bp.route("/track/click", methods=["POST"])
@csrf.exempt
def track_click():
    data = request.get_json() or {}
    entity_type = data.get("entity_type")
    entity_id = data.get("entity_id")
    context_id = data.get("context_id")
    
    if not entity_type or not entity_id:
        return jsonify({"success": False, "error": "Missing parameters"}), 400
        
    user_id = current_user.id if current_user.is_authenticated else None
    
    success = track_click_workflow(entity_type, entity_id, context_id, user_id)
    
    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Failed to track click"}), 500

@bp.route("/collection/rename", methods=["POST"])
@login_required
@csrf.exempt
def rename_collection_route():
    data = request.get_json() or {}
    old_name = data.get("old_name")
    new_name = data.get("new_name")
    
    if not old_name or not new_name:
        return jsonify({"success": False, "error": "Missing parameters"}), 400
        
    from app.domains.interaction.service.command import rename_collection
    result = rename_collection(current_user, old_name, new_name)
    return jsonify(result), (200 if result.get("success") else 400)

@bp.route("/collection/delete", methods=["POST"])
@login_required
@csrf.exempt
def delete_collection_route():
    data = request.get_json() or {}
    collection_name = data.get("collection_name")
    move_to_global = data.get("move_to_global", False)
    
    if not collection_name:
        return jsonify({"success": False, "error": "Missing parameters"}), 400
        
    from app.domains.interaction.service.command import delete_collection
    result = delete_collection(current_user, collection_name, move_to_global)
    return jsonify(result), (200 if result.get("success") else 400)

@bp.route("/save/move", methods=["POST"])
@login_required
@csrf.exempt
def move_save_route():
    data = request.get_json() or {}
    target_type = data.get("target_type")
    target_id = data.get("target_id")
    new_collection_name = data.get("new_collection_name")
    old_collection_name = data.get("old_collection_name")
    
    if not target_type or not target_id or not new_collection_name:
        return jsonify({"success": False, "error": "Missing parameters"}), 400
        
    try:
        from app.shared.parsing import parse_target_type
        target_type_parsed = parse_target_type(target_type)
    except ValueError:
        return jsonify({"success": False, "error": "Invalid target type"}), 400
        
    from app.domains.interaction.service.command import move_save_collection
    result = move_save_collection(current_user, target_type_parsed, target_id, new_collection_name, old_collection_name)
    return jsonify(result), (200 if result.get("success") else 400)
