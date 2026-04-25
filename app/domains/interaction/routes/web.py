from . import bp

from datetime import datetime, timedelta, timezone
from flask import request, jsonify, render_template, redirect, url_for, flash, abort, current_app, Blueprint
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError
from ..models import Reaction, Comment, Save, ItemClick
from app.core.extensions import limiter, db
from app.domains.user.models import NewsletterSubscriber
from app.domains.article.models import Article
from app.domains.item.models import Item, ItemStoreLink
from app.shared.constants.core import TargetType
from ..constants import INTERACTION_TYPE
from app.shared.parsing import parse_target_type, parse_interaction_type
from app.shared.request import get_client_ip
from app.domains.user.email_service import send_confirmation_email
from app.core.context import get_newsletter_context
from ..service import react, save_item, post_comment, record_view
from app.domains.recommendation.interest_service import handle_interaction_interest, handle_comment_interaction
# Subscribe route
# ------------------------
@bp.route('/subscribe', methods=['POST'])
def subscribe():
    try:
        # 🔹 Determine email
        if current_user.is_authenticated:
            email = current_user.email
            user_id = current_user.id
        else:
            email = request.form.get('email')
            user_id = None

        if not email:
            return jsonify({'success': False, 'error': 'Email is required.'})

        # 🔹 Check existing subscriber
        subscriber = NewsletterSubscriber.query.filter_by(email=email).first()

        if subscriber:
            # Re-link user if needed
            if user_id:
                subscriber.user_id = user_id

            # Already active
            if subscriber.is_active:
                return jsonify({
                    'success': False,
                    'error': 'You are already subscribed.'
                })

            subscriber.unsubscribed_at = None

            # Resend confirmation
            if not subscriber.is_confirmed:
                subscriber.generate_tokens()

        else:
            subscriber = NewsletterSubscriber(
                email=email,
                user_id=user_id
            )
            subscriber.generate_tokens()
            db.session.add(subscriber)

        db.session.commit()
        # 🔥 TODO: send email here
        # send_confirmation_email(subscriber.email, subscriber.confirmation_token)
        send_confirmation_email(
            subscriber.email,
            subscriber.confirmation_token,
            subscriber.unsubscribe_token
        )

        return jsonify({
            'success': True,
            'message': 'Check your email to confirm subscription 📬',
            'html': render_template(
                'partials/newsletter-block.html',
                **get_newsletter_context()
            )            
        })

    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Something went wrong. Please try again.'
        })

@bp.route('/confirm-subscription/<token>')
def confirm_subscription(token):
    subscriber = NewsletterSubscriber.query.filter_by(
        confirmation_token=token
    ).first()

    if not subscriber:
        flash("Invalid or expired confirmation link.", "error")
        return redirect(url_for('system.home'))
    
    subscriber.is_confirmed = True
    subscriber.confirmation_token = None
    subscriber.unsubscribed_at = None

    db.session.commit()

    flash("Your subscription has been confirmed 🎉", "success")
    return redirect(url_for('system.home'))

@bp.route('/unsubscribe-auth', methods=['POST'])
@login_required
def unsubscribe_auth():
    subscriber = current_user.newsletter_subscription

    if not subscriber or not subscriber.is_active:
        return jsonify({
            'success': False,
            'error': 'You are not subscribed.'
        })

    subscriber.unsubscribed_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'You have unsubscribed.',
        'html': render_template(
            'partials/newsletter-block.html',
            **get_newsletter_context()
        )
    })

@bp.route('/unsubscribe/<token>')
def unsubscribe_token(token):
    subscriber = NewsletterSubscriber.query.filter_by(
        unsubscribe_token=token
    ).first()

    if not subscriber:
        flash("Invalid unsubscribe link.", "error")
        return redirect(url_for('system.home'))

    subscriber.unsubscribed_at = datetime.now(timezone.utc)
    db.session.commit()

    flash("You have been unsubscribed successfully.", "success")
    return redirect(url_for('system.home'))    

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
            target_type = parse_target_type(t_str)
        except ValueError:
            continue
        try:
            target_id = int(id_str)
        except (TypeError, ValueError):
            continue  # skip invalid
        reaction = Reaction.query.filter_by(
            user_id=current_user.id,
            target_type=target_type,
            target_id=target_id
        ).first()
        # result[f"{t_str}:{id_str}"] = reaction.type if reaction else None
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
        except ValueError:
            continue
        try:
            target_id = int(id_str)
        except (TypeError, ValueError):
            continue
        if target_type == TargetType.ARTICLE:
            target = Article.query.get(target_id)
        elif target_type == TargetType.ITEM:
            target = Item.query.get(target_id)
        else:
            target = None
        if not target:
            continue
        saved = Save.query.filter_by(
            user_id=current_user.id,
            target_type=target_type,
            target_id=target_id
        ).first()
        if saved:
            result[f"{t_str}:{id_str}"] = True
    return jsonify(result)

@bp.route("/get-comments")
def get_comments():
    params = request.args
    try:
        target_type = parse_target_type(params.get("type"))
    except ValueError:
        abort(400, "Invalid target type")
    
    try:
        target_id = int(params.get("id"))
    except (TypeError, ValueError):
        abort(400, "Invalid target id")


    query = Comment.query.filter_by(
        target_type=target_type,
        target_id=target_id
    )

    # IMPORTANT: check if param EXISTS, not just its value
    if "parent_id" in params:
        parent_id = params.get("parent_id", type=int)
        query = query.filter_by(parent_id=parent_id)
    else:
        # load root comments only
        query = query.filter_by(parent_id=None)
    
    comments = query.order_by(Comment.created_at.asc()).all()

    comments_html = "".join(render_template('components/features/comment-card.html', comment=c, is_reply="parent_id" in params) for c in comments)

    return comments_html

@bp.route("/item-click/<int:link_id>", methods=["POST"])
def item_click(link_id):
    link = ItemStoreLink.query.get_or_404(link_id)
    user_id = current_user.id if current_user.is_authenticated else None
    ip_address = request.remote_addr if not user_id else None
    last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    # 🔒 Deduplicate click
    existing = ItemClick.query.filter(
        ItemClick.item_store_link_id == link.id,
        ItemClick.created_at >= last_24h,
        (
            ItemClick.user_id == user_id
            if user_id else
            ItemClick.ip_address == ip_address
        )
    ).first()
    if not existing:
        try:
            click = ItemClick(
                item_store_link_id=link.id,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=request.headers.get("User-Agent"),
                referrer=request.referrer,
                country=request.headers.get("CF-IPCountry")
            )
            db.session.add(click)
            # 🔢 increment item click_count once per 24h
            link.item.click_count = (link.item.click_count or 0) + 1
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print("Click tracking failed:", e)
    # Optional: user interaction tracking — fully isolated
    if current_user.is_authenticated:
        try:
            handle_interaction_interest(
                user=current_user,
                target=link.item,
                action="item_click"
            )
        except Exception as e:
            print("Interaction tracking failed:", e)
    return jsonify({"redirect_url": link.affiliate_url})

@bp.route("/view", methods=["POST"])
def add_view():
    try:
        target_type = parse_target_type(request.form.get("type"))
    except ValueError:
        abort(400, "Invalid target type")
    try:
        target_id = int(request.form.get("id"))
    except (TypeError, ValueError):
        abort(400, "Invalid target id")
    user = current_user if current_user.is_authenticated else None
    ip = None if user else get_client_ip()
    if target_type == TargetType.ARTICLE:
        target = Article.query.get_or_404(target_id)
    else:
        target = Item.query.get_or_404(target_id)
    result = record_view(
        target=target,
        target_type=target_type,
        user=user,
        ip_address=ip,
    )
    return jsonify(result)


@bp.route("/handle-interaction", methods=["POST"])
@login_required
@limiter.limit("5 per minute")
def handle_interaction():
    try:
        target_type = parse_target_type(request.form.get("type"))
        target_id = int(request.form.get("id"))
        comment_id = request.form.get('comment_id', None, type=int)
        interaction_type = parse_interaction_type(request.form.get("interaction_type"))
        if comment_id:
            target = Comment.query.get_or_404(comment_id)
        elif target_type == TargetType.ARTICLE:
            target = Article.query.get_or_404(target_id)
        elif target_type == TargetType.ITEM:
            target = Item.query.get_or_404(target_id)
        else:
            abort(400)
        result = None
        action = interaction_type
        if interaction_type == INTERACTION_TYPE.REACT:
            reaction_type = request.form.get("reaction")
            if comment_id:
                result = react(current_user, 'comment', comment_id, reaction_type, target)
            else:
                result = react(current_user, target_type, target_id, reaction_type)
            action = reaction_type
        elif interaction_type == INTERACTION_TYPE.SAVE:
            # if target_type == TargetType.COMMENT:
            #     abort(400)
            result = save_item(current_user, target_type, target_id)
        elif interaction_type == INTERACTION_TYPE.COMMENT:
            content = request.form.get("comment", "").strip()
            result = post_comment(
                current_user,
                target_type,
                target_id,
                content,
                comment_id
            )
        if not result.get("success"): return jsonify(result), 400
        if not comment_id:
            handle_interaction_interest(user=current_user, target=target, action=action)
            if interaction_type == INTERACTION_TYPE.COMMENT:
                target.comment_count = (target.comment_count or 0) + 1
                handle_comment_interaction(user=current_user, target=target, comment_sentiment=result.get("sentiment"))
        db.session.commit()
        return jsonify(result)
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Interaction failed")
        abort(500, "Interaction failed")

@bp.route('/saved')
@login_required
def saved_items():
    """Display all articles and items saved by the current user."""
    # Query saves for current user, grouped by type
    saved_articles = (
        Save.query.options(db.selectinload(Save.article))
        .filter_by(user_id=current_user.id, target_type=TargetType.ARTICLE)
        .order_by(Save.created_at.desc())
        .all()
    )
    
    saved_items = (
        Save.query.options(db.selectinload(Save.item))
        .filter_by(user_id=current_user.id, target_type=TargetType.ITEM)
        .order_by(Save.created_at.desc())
        .all()
    )
    
    return render_template(
        'saved-items.html',
        saved_articles=saved_articles,
        saved_items=saved_items
    )
