from flask import Blueprint, request, render_template, jsonify, current_app, make_response, url_for
import os
from datetime import datetime
from app.application.system.home import get_home_page_data
from app.application.system.contact import send_contact_message_workflow
from app.domains.content.service import get_latest_contents
from app.domains.system.pages_service import PAGES_CONTENT

bp = Blueprint("system", __name__)

@bp.route("/set-country", methods=["POST"])
def set_country():
    country = request.json.get("country")
    response = jsonify({"success": True})
    if country:
        response.set_cookie("country", country.lower(), max_age=60*60*24*365)
    else:
        response.delete_cookie("country")
    return response

@bp.route('/')
def home():
    data = get_home_page_data()
    return render_template("index.html", **data)

@bp.route('/about')
def about():
    return render_template('about.html', cover_cards=PAGES_CONTENT.get('about', []))

@bp.route('/contact')
def contact():
    return render_template('contact.html', contact_cards=PAGES_CONTENT.get('contact', []))

@bp.route("/contact", methods=["POST"])
def send_contact_message():
    data = {k: request.form.get(k, "").strip() for k in ("name", "email", "subject", "message")}
    
    success, message = send_contact_message_workflow(
        data,
        request.remote_addr,
        request.headers.get("User-Agent")
    )
    
    return jsonify({
        "success": success,
        "message" if success else "error": message
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

@bp.route('/sitemap.xml')
def sitemap():
    try:
        sitemap_path = os.path.join(current_app.static_folder, 'sitemap.xml')
        if os.path.exists(sitemap_path):
            with open(sitemap_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return make_response(content, 200, {'Content-Type': 'application/xml'})
    except Exception as e:
        current_app.logger.error("Error serving static sitemap: %s", e)

    pages = []
    for rule in current_app.url_map.iter_rules():
        if "GET" in rule.methods and len(rule.arguments) == 0:
            pages.append([url_for(rule.endpoint, _external=True), datetime.now().date().isoformat()])

    contents = get_latest_contents(limit=100)
    for content in contents:
        pages.append([url_for('content.content_page', content_id=content.id, _external=True),
                      (content.published_at or datetime.now()).date().isoformat()])

    response = make_response(render_template('sitemap_xml.html', pages=pages))
    response.headers['Content-Type'] = 'application/xml'
    return response
