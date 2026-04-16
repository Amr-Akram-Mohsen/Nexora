# app/utils/sitemap_generator.py
import os
from datetime import datetime
from flask import url_for
from app.models import Article, Item

def generate_static_sitemap(app):
    """Generates a static sitemap.xml file in the static folder."""
    # Use test_request_context so url_for knows how to build external URLs
    # You can change 'localhost' to your production domain eventually
    base_url = app.config.get('SERVER_NAME') or 'localhost:5000'
    if not base_url.startswith(('http://', 'https://')):
        base_url = 'https://' + base_url

    with app.test_request_context(base_url=base_url):
        pages = []
        
        # 1. Static Routes
        for rule in app.url_map.iter_rules():
            # Only GET rules with no arguments
            if "GET" in rule.methods and len(rule.arguments) == 0:
                pages.append([url_for(rule.endpoint, _external=True), datetime.now().date().isoformat()])

        # 2. Articles
        articles = Article.query.all()
        for article in articles:
            pages.append([
                url_for('main.article_page', article_id=article.id, _external=True),
                (article.published_at or datetime.now()).date().isoformat()
            ])

        # 3. Items
        items = Item.query.all()
        for item in items:
            pages.append([
                url_for('main.item_page', item_id=item.id, _external=True),
                (item.created_at or datetime.now()).date().isoformat()
            ])

        # Render
        from flask import render_template
        sitemap_xml = render_template('sitemap_xml.html', pages=pages)
        
        static_folder = app.static_folder
        if not os.path.exists(static_folder):
            os.makedirs(static_folder)
            
        output_path = os.path.join(static_folder, 'sitemap.xml')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(sitemap_xml)
            
        return len(pages)
