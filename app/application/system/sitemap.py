import os
from datetime import datetime, timezone
from flask import url_for
from app.domains.taxonomy.service.query import get_active_sections
from app.domains.content.service.query.filtering import get_all_contents_metadata
from app.domains.product.service.query import get_all_items_metadata


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
        sections = get_active_sections()
        for section in sections:
            pages.append(
                [
                    url_for(
                        "content.sections", section_slug=section["slug"], _external=True
                    ),
                    today,
                ]
            )

        # 3. Contents
        contents = get_all_contents_metadata()
        for content_id, updated_at, published_at in contents:
            last_mod = (
                (
                    updated_at
                    or published_at
                    or datetime.now(timezone.utc)
                )
                .date()
                .isoformat()
            )
            pages.append(
                [
                    url_for(
                        "content.content_page", content_id=content_id, _external=True
                    ),
                    last_mod,
                ]
            )

        # 4. Items (id + created_at only — avoid loading full product graphs)
        product_rows = get_all_items_metadata()
        for product_id, created_at in product_rows:
            last_mod = (
                (created_at or datetime.now(timezone.utc)).date().isoformat()
            )
            pages.append(
                [url_for("product.item_page", product_id=product_id, _external=True), last_mod]
            )


        # Render Sitemap XML Chunks
        from flask import render_template
        
        static_folder = os.path.join(app.static_folder, "sitemaps")
        if not os.path.exists(static_folder):
            os.makedirs(static_folder)
            
        # Clean existing chunks
        for f in os.listdir(static_folder):
            if f.endswith(".xml"):
                os.remove(os.path.join(static_folder, f))

        chunk_size = 1000
        chunks = []
        
        for i in range(0, len(pages), chunk_size):
            chunk_pages = pages[i:i + chunk_size]
            chunk_idx = (i // chunk_size) + 1
            
            sitemap_xml = render_template("sitemap_xml.html", pages=chunk_pages)
            chunk_filename = f"sitemap_{chunk_idx}.xml"
            output_path = os.path.join(static_folder, chunk_filename)
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(sitemap_xml)
                
            chunks.append({
                "url": url_for("system.sitemap_chunk", chunk=chunk_idx, _external=True),
                "lastmod": today
            })
            
        # Write Index
        index_xml = render_template("sitemap_index_xml.html", chunks=chunks)
        index_path = os.path.join(static_folder, "sitemap_index.xml")
        
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_xml)

        return len(pages)
