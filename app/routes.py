# app/routes.py
from flask import (
    current_app,
    Blueprint,
    render_template,
    abort,
    request,
    flash,
    redirect,
    url_for,
    jsonify
)
from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user
)
from random import shuffle
from app.helpers.context import get_global_context, get_newsletter_context
from app.services.mailer import send_admin_email
from app.constants import TargetType, INTERACTION_TYPE
from app.services.pages_content import PAGES_CONTENT
from app.services.store_service import prepare_store_links
from app.services.interaction_service import *
from app.services.interest_service import (
    handle_interaction_interest,
    handle_comment_interaction
)
from app.services.item_service import filter_items_by_country, get_search_items
from app.services.article_service import *
from app.utils.parsing import parse_target_type, parse_interaction_type
from app.utils.request import get_client_ip, get_country
from sqlalchemy import func, or_

from datetime import datetime, timedelta
from app.models import (
    Article,
    Section,
    Category,
    Brand,
    Topic,
    User,
    NewsletterSubscriber,
    Item,
    ItemVariant,
    Comment,
    Reaction,
    Save,
    ItemClick,
    ItemStoreLink,
    ContactMessage,
    db)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
bp = Blueprint('main', __name__, static_folder='static')
# ------------------------
# Login route
# ------------------------

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.home'))
        flash('Invalid email or password', 'error')
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        wants_newsletter = request.form.get('subscribe') is not None
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return redirect(url_for('main.register'))
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        newsletter_msg = None
        subscriber = NewsletterSubscriber.query.filter_by(email=email).first()
        if subscriber:
            subscriber.user_id = user.id
            if wants_newsletter:
                newsletter_msg = 'Your existing newsletter subscription was linked 🎯'
            else:
                newsletter_msg = 'You already have subscribed to the newsletter with this email before'
        if wants_newsletter and not subscriber:
            db.session.add(NewsletterSubscriber(
                email=email,
                user_id=user.id,
                is_active=False
            ))
            newsletter_msg = 'You\'ve been subscribed to the newsletter 📬'
        db.session.commit()
        login_user(user)
        flash('Registration completed successfully 🎉', 'success')
        if newsletter_msg:
            flash(newsletter_msg, 'info')
        return redirect(url_for('main.home'))
    return render_template('register.html')

# Logout route

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.home'))


# Specifying Country Using Cookies
@bp.route("/set-country", methods=["POST"])
def set_country():
    country = request.json.get("country")

    response = jsonify({"success": True})

    if country:
        response.set_cookie("country", country.lower(), max_age=60*60*24*365)
    else:
        # clear cookie if user selects "All"
        response.delete_cookie("country")

    return response
# Subscribe route
# ------------------------

@bp.route('/subscribe', methods=['POST'])
def subscribe():
    message = None
    try:
        mode = request.form.get('mode')
        email = None
        user_id = None
        # Guest user
        if not current_user.is_authenticated:
            if mode == 'account':
                message = 'You must be logged in to use account subscription.'
            else:
                email = request.form.get('email')
        # Logged-in user
        else:
            if mode not in ('guest', 'account'):
                message = 'Invalid subscription mode.'
            else:
                guest_email, curr_email = request.form.getlist('email')
                if mode == 'guest' and not guest_email:
                    message = 'Please, fill in this field.'
                else:
                    if mode == 'account':
                        email = curr_email
                        user_id = current_user.id
                    else:
                        email = guest_email
        # Stop early if error happened
        if message:
            return jsonify({
                'success': False,
                'error': message
                })
        # Check if email belongs to another user
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and (not current_user.is_authenticated or existing_user.id != current_user.id):
            return jsonify({
                'success': False,
                'error': 'This email is registered by another user. Please use your own account to subscribe.'
                })
        # Check existing subscription
        subscriber = NewsletterSubscriber.query.filter_by(email=email).first()
        if subscriber and not subscriber.unsubscribed_at:
            return jsonify({
                'success': False,
                'error': 'This email is already subscribed.'
                })
        # Re-subscribe or create
        if subscriber:
            subscriber.unsubscribed_at = None
            if user_id:
                subscriber.user_id = user_id
        else:
            subscriber = NewsletterSubscriber(
                email=email,
                user_id=user_id,
                is_active=True
            )
            db.session.add(subscriber)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'You have subscribed to the newsletter 📬',
            'html': render_template(
                    'partials/newsletter-block.html',
                    **get_newsletter_context()
                )
            })
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'An error occurred. Please try again.'
            })

@bp.route('/unsubscribe', methods=['POST'])
@login_required
def unsubscribe():
    subscriber = current_user.newsletter_subscription
    if not subscriber or subscriber.unsubscribed_at:
        return jsonify({
            'success': False,
            'error': 'You are not subscribed.'
            })
    subscriber.unsubscribed_at = datetime.utcnow()
    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'You have unsubscribed from the newsletter.',
        'html': render_template(
                'partials/newsletter-block.html',
                **get_newsletter_context()
            )
        })

# ============== SEARCH LOGIC ================
@bp.route('/search', methods=['POST'])
def search():
    q = (request.form.get('query') or '').strip()

    items = get_search_items(q)
    articles = get_search_articles(q)    

    search_results = articles + items
    shuffle(search_results)

    # If AJAX request, return only the grid HTML
    
    return jsonify({
        'success': True,
        'html': render_template(
            'search-results.html',
            search_results=search_results,
            query=q,
            country=get_country()
        )
    })

@bp.app_context_processor
def inject_global_context():
    return get_global_context()

@bp.route('/')
def home():
    hero_articles = get_articles(filter_values=('trends',), rows_count=3)
    latest_reviews = get_articles(filter_values=('reviews',), rows_count=3)
    tech_news = get_articles(filter_values=('news',), rows_count=3)
    tutorials = get_articles(filter_values=('tutorials',), rows_count=3)
    # --- DB-backed items ---
    p_query = Item.query.options(
        db.joinedload(Item.brand),
        db.joinedload(Item.category),
        db.joinedload(Item.images)
    )

    # random_items = filter_items_by_country(p_query).limit(10).all()
    random_items = p_query.limit(10).all()
    
    return render_template(
        "index.html",
        hero_sliders=hero_articles,
        latest_reviews=latest_reviews,
        tech_news=tech_news,
        tutorials=tutorials,
        items=random_items
    )

@bp.route("/sections/<section_slug>")
def sections(section_slug):
    section = Section.query.filter(
        func.lower(Section.name) == section_slug,
        Section.is_active == True
    ).first_or_404()


    category = request.args.get("category_slug")
    topics = request.args.getlist("topic_slug")
    brands = request.args.getlist("brand_slug")

    query = (
        Article.query
        .join(Article.sections)
        .filter(Section.id == section.id,
        Category.slug == category)
    )

    allowed_filters = set(section.allowed_filters or [])
    
    if topics and "topic" in allowed_filters:
        query = query.join(Article.topics).filter(Topic.slug.in_(topics))
    if brands and "brand" in allowed_filters:
        query = query.join(Article.brands).filter(Brand.slug.in_(brands))
    
    articles = (
        query
        .distinct()
        .order_by(Article.published_at.desc())
        .limit(50)
        .all()
    )

    filter_options = {}
    active_filters = {}

    if "brand" in allowed_filters:
        filter_options["brand"] = get_active_brands_for_section(section_slug)
        active_filters['brand'] = brands
    if "topic" in allowed_filters:
        filter_options["topic"] = get_active_topics_for_section(section_slug)
        active_filters['topic'] = topics
    return render_template(
        "sections-page.html",
        section=section,
        articles=articles,
        allowed_filters=allowed_filters,
        filter_options=filter_options,
        active_filters=active_filters
    )

@bp.route('/about')
def about():
    return render_template('about.html', cover_cards=PAGES_CONTENT.get('about', []))

@bp.route('/contact')
def contact():
    return render_template('contact.html', contact_cards=PAGES_CONTENT.get('contact', []))

@bp.route("/contact", methods=["POST"])
def send_contact_message():
    data = {k: request.form.get(k, "").strip() for k in
            ("name", "email", "subject", "message")}

    if not all(data.values()):
        return jsonify({
            "success": False,
            "error": "One or more fields are empty!!"
            })

    msg = ContactMessage(
        **data,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent")
    )

    db.session.add(msg)
    db.session.commit()

    send_admin_email(data)  # wrapped function

    current_app.logger.info(
        "Contact message saved (id=%s) from %s",
        msg.id, data["email"]
    )

    return jsonify({
        "success": True,
        "message": "Message sent successfully!!"
        })

@bp.route('/privacy')
def privacy():
    return render_template('privacy.html', content=PAGES_CONTENT.get('privacy'))

@bp.route('/terms')
def terms():
    return render_template('terms.html', content=PAGES_CONTENT.get('terms'))

@bp.route('/affiliate')
def affiliate():
    return render_template('affiliate.html', content=PAGES_CONTENT.get('affiliate'))

@bp.route("/items")
def items():
    query = Item.query.options(
        db.joinedload(Item.brand),
        db.joinedload(Item.category),
        db.joinedload(Item.images)
    )

    # prods = filter_items_by_country(query).limit(20).all()
    prods = query.limit(20).all()

    return render_template('items-page.html',
                           category='Items',
                           items=prods)

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
        elif target_type == TargetType.PRODUCT:
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
    last_24h = datetime.utcnow() - timedelta(hours=24)
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

@bp.route("/item/<int:item_id>/view_full_specs", methods=["POST"])
def view_full_specs(item_id):
    item = Item.query.get_or_404(item_id)
    html = render_template(
        "components/features/full-specs.html",
        full_specs=item.full_specs
    )
    return jsonify({
        "html": html
    })

@bp.route("/articles/<int:article_id>")
def article_page(article_id):
    article = Article.query.get_or_404(article_id)
    user = current_user if current_user.is_authenticated else None
    ip = None if user else get_client_ip()
    record_view(
        target=article,
        target_type=TargetType.ARTICLE,
        user=user,
        ip_address=ip
    )
    section_ids = [s.id for s in article.sections]
    related_articles = get_related_articles(article)
    trending_articles = get_trending_articles(limit=6, days=7, section_ids=section_ids)
    
    return render_template(
        "article-page.html",
        article=article,
        related_articles=related_articles,
        trending_articles=trending_articles
    )

@bp.route("/items/<int:item_id>")
def item_page(item_id):
    item = Item.query.options(
        db.selectinload(Item.variants)
            .selectinload(ItemVariant.store_links)
            .selectinload(ItemStoreLink.store),
        db.selectinload(Item.images)
    ).get_or_404(item_id)

    user = current_user if current_user.is_authenticated else None
    ip = None if user else get_client_ip()
    record_view(
        item,
        TargetType.PRODUCT,
        user,
        ip)
    # analytics = get_item_analytics(item.id)
    # top_store = get_top_store_for_item(item.id)
    # print(f'\nAnalytics\n{analytics}')
    # print(f'\nTop Store\n{top_store}')
    return render_template(
        "item-page.html",
        item=item
    )

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
    if target_type == TargetType.ARTICLE:
        _ = Article.query.get_or_404(target_id)
    else:
        _ = Item.query.get_or_404(target_id)
    result = record_view(target_type, target_id)
    return jsonify(result)

@bp.route("/handle-interaction", methods=["POST"])
@login_required
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
        elif target_type == TargetType.PRODUCT:
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


