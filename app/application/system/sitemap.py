import os
from datetime import datetime, timezone
from flask import url_for
from app.domains.content.models import Content
from app.domains.item.models import Item
from app.domains.system.models import Section


def generate_static_sitemap(app):
    """Generates a static sitemap.xml file in the static folder."""
    # Production-ready base URL logic
    base_url = app.config.get("SERVER_NAME") or "nexora.com"
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url

    with app.test_request_context(base_url=base_url):
        pages = []
        today = datetime.now(timezone.utc).date().isoformat()

        # 1. Static Routes (Home, deals, etc.)
        for rule in app.url_map.iter_rules():
            # Only GET rules with no arguments (top-level pages)
            if "GET" in rule.methods and len(rule.arguments) == 0:
                try:
                    pages.append([url_for(rule.endpoint, _external=True), today])
                except Exception:
                    continue

        # 2. Sections (Catalog pages)
        sections = Section.query.filter_by(is_active=True).all()
        for section in sections:
            pages.append(
                [
                    url_for(
                        "content.sections", section_slug=section.slug, _external=True
                    ),
                    today,
                ]
            )

        # 3. Contents
        contents = Content.query.all()
        for content in contents:
            last_mod = (
                (
                    content.updated_at
                    or content.published_at
                    or datetime.now(timezone.utc)
                )
                .date()
                .isoformat()
            )
            pages.append(
                [
                    url_for(
                        "content.content_page", content_id=content.id, _external=True
                    ),
                    last_mod,
                ]
            )

        # 4. Items
        items = Item.query.all()
        for item in items:
            last_mod = (
                (item.updated_at or item.created_at or datetime.now(timezone.utc))
                .date()
                .isoformat()
            )
            pages.append(
                [url_for("item.item_page", item_id=item.id, _external=True), last_mod]
            )

        # Render Sitemap XML
        from flask import render_template

        sitemap_xml = render_template("sitemap_xml.html", pages=pages)

        static_folder = app.static_folder
        if not os.path.exists(static_folder):
            os.makedirs(static_folder)

        output_path = os.path.join(static_folder, "sitemap.xml")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(sitemap_xml)

        return len(pages)
