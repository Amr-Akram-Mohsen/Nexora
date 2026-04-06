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
    random_items = p_query.order_by(Item.id.asc()).limit(10).all()
    
    return render_template(
        "index.html",
        hero_sliders=hero_articles,
        latest_reviews=latest_reviews,
        tech_news=tech_news,
        tutorials=tutorials,
        items=random_items
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
