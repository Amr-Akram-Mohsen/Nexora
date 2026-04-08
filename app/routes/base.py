from flask import request, render_template, jsonify, current_app

from app.models import db, ContactMessage, Item
from app.services.mailer import send_admin_email
from app.services.pages_content import PAGES_CONTENT
from app.services.article_service import get_articles
from . import bp

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


@bp.route('/')
def home():
    from app.models import ItemVariant

    hero_articles = get_articles(filter_values=('trends',), rows_count=3)
    latest_reviews = get_articles(filter_values=('reviews',), rows_count=6)
    tech_news = get_articles(filter_values=('news',), rows_count=6)
    tutorials = get_articles(filter_values=('tutorials',), rows_count=6)
    
    # Base item query
    p_query = Item.query.options(
        db.joinedload(Item.brand),
        db.joinedload(Item.category),
        db.selectinload(Item.images),
        db.selectinload(Item.variants).selectinload(ItemVariant.store_links)
    )

    # Top deals: items with a discount Note: you can also order by (ItemVariant.old_price - ItemVariant.price).desc() but simple filter works for now
    top_deals = p_query.join(Item.variants).filter(ItemVariant.old_price > ItemVariant.price).limit(10).all()
    if not top_deals:
        top_deals = p_query.order_by(Item.id.desc()).limit(10).all()
        
    recently_added = p_query.order_by(Item.created_at.desc()).limit(10).all()
    
    # Generic Items for interleaving
    interleave_items = p_query.order_by(db.func.random()).limit(10).all()
    interleave_pool = list(interleave_items)
    
    def interleave(articles, items_pool):
        result = []
        for i, article in enumerate(articles):
            result.append(article)
            if (i + 1) % 3 == 0 and items_pool:
                result.append(items_pool.pop(0))
        return result

    return render_template(
        "index.html",
        hero_sliders=hero_articles,
        latest_reviews=interleave(latest_reviews, interleave_pool),
        tech_news=interleave(tech_news, interleave_pool),
        tutorials=interleave(tutorials, interleave_pool),
        top_deals=top_deals,
        recently_added=recently_added
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
