from datetime import datetime


def serialize_model(m):
    if not m:
        return None
    return {
        "name": getattr(m, "name", None),
        "slug": getattr(m, "slug", None),
    }


def serialize_target(obj, session=None):
    """
    Serializes a polymorphic target object (Article, Video, Post, or Product).
    Ensures all type-specific fields are present for a premium UI.
    """
    if not obj:
        return None

    # Determine type name (e.g., 'article', 'video', 'post', 'product')
    type_name = obj.__class__.__name__.lower()

    # Core fields common to most targets
    data = {
        "id": getattr(obj, "id", None),
        "type": type_name,
        "title": getattr(obj, "title", None) or getattr(obj, "name", None),
        "preview_text": getattr(obj, "preview_text", None),
        "url": getattr(obj, "url", None),
        "image_url": getattr(obj, "image_url", None)
        or getattr(obj, "thumbnail_url", None),
    }

    # ── Type-Specific Enrichment ─────────────────────────────────────
    
    def _normalize_authors(raw_authors):
        import re
        
        def slugify(text):
            if not text:
                return ""
            return re.sub(r'[-\s]+', '-', re.sub(r'[^\w\s-]', '', text.lower())).strip('-')
            
        if not raw_authors:
            return []
        if isinstance(raw_authors, str):
            raw_authors = [raw_authors]
        
        normalized = []
        for a in raw_authors:
            if isinstance(a, str):
                normalized.append({"name": a, "slug": slugify(a)})
            elif isinstance(a, dict) and a.get("name"):
                name = a["name"]
                slug = slugify(name)
                url = a.get("link") if a.get("link") else a.get("uri") if a.get("uri") else None
                normalized.append({"name": name, "slug": slug, "url": url})
        return normalized

    def _serialize_authors(authors):
        return [{
                    "id": a.id,
                    "name": a.name,
                    "slug": a.slug,
                    "url": a.url,
                    "icon_url": a.icon_url,
                    "is_agency": a.is_agency,
                } for a in authors
            ]

    # def _serialize_sources(sources):
    #     return [{
    #                 "id": s.id,
    #                 "url": s.url,
    #                 "published_at": s.published_at,
    #                 "source": {
    #                     "id": s.source.id,
    #                     "name": s.source.name,
    #                     "slug": s.source.slug,
    #                     "logo_url": s.source.logo_url,
    #                 }
    #             } for s in sources
    #         ]

    def _serialize_sources(sources):
        return [{
                    "name": s.source.name,
                    "slug": s.source.slug,
                    "url": s.url,
                    "published_at": s.published_at,
                    "logo_url": s.source.logo_url,
                    "authority_score": s.source.authority_score,
                } for s in sources
            ]

    if type_name == "article":

        # print(f"\n\n{type(obj.authors)}\n\n")
        # Derive is_content_scraped from status or content_html presence
        status = getattr(obj, "status", None)
        is_content_scraped = status in ("ready", "published", "complete") or bool(getattr(obj, "content_html", None))
        
        # Serialize primary source relation cleanly
        rel = getattr(obj, "primary_source", None)
        # primary_source = serialize_model(primary_source_rel.source) if primary_source_rel and primary_source_rel.source else None

        # primary_source = {
        #     "id": rel.id,
        #     "url": rel.url,
        #     "published_at": rel.published_at,

        #     "source": {
        #         "id": rel.source.id,
        #         "name": rel.source.name,
        #         "slug": rel.source.slug,
        #         "logo_url": rel.source.logo_url,
        #         "authority_score": rel.source.authority_score,
        #     }
        # }
        primary_source = {
            "name": rel.source.name,
            "slug": rel.source.slug,
            "url": rel.url,
            "published_at": rel.published_at,
            "logo_url": rel.source.logo_url,
            "authority_score": rel.source.authority_score
        }
        
        serialized_authors = _serialize_authors(obj.authors)
        data.update(
            {
                "source_name": obj.source_name,
                "source_url": obj.source_url,
                "read_time_minutes": obj.read_time_minutes,
                "is_content_scraped": is_content_scraped,
                "author": serialized_authors[0] if serialized_authors else None,
                "authors": _serialize_authors(obj.authors),
                "sources": _serialize_sources(obj.article_sources),
                "content_text": getattr(obj, "content_text", None),
                "content_html": getattr(obj, "content_html", None),
                "summary": getattr(obj, "summary", None),
                "body": getattr(obj, "body", None),
                "description": getattr(obj, "description", None),
                "word_count": getattr(obj, "word_count", 0),
                "sentiment_score": getattr(obj, "sentiment_score", None),
                "event": serialize_model(getattr(obj, "event", None)),
                "primary_source": primary_source,
            }
        )

    elif type_name == "video":
        data.update(
            {
                "platform": getattr(obj, "platform", "youtube"),
                "external_id": getattr(obj, "external_id", None),
                "channel_name": getattr(obj, "channel_name", "Unknown"),
                "description": getattr(obj, "description", None),
                "thumbnail_url": getattr(obj, "thumbnail_url", None),
                "duration_seconds": getattr(obj, "duration_seconds", None),
            }
        )

    elif type_name == "post":
        data.update(
            {
                "platform": getattr(obj, "platform", "reddit"),
                "external_id": getattr(obj, "external_id", None),
                "author": getattr(obj, "author", "Unknown"),
                "subreddit": getattr(obj, "subreddit", None),
                "upvotes": getattr(obj, "upvotes", 0),
                "body": getattr(obj, "body", None),
            }
        )

    elif type_name == "product":
        from app.domains.product.serializers import serialize_item
        
        item_data = serialize_item(obj)
        if item_data:
            data.update(item_data)
            # Unify basic target keys from item_data
            data["title"] = item_data.get("name")
            data["brand_name"] = item_data.get("brand", {}).get("name") if item_data.get("brand") else None
            data["category_name"] = item_data.get("category", {}).get("name") if item_data.get("category") else None

    return data

