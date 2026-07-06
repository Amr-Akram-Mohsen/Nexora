def get_platform_icon(platform_name):
    platform_icons = {
        "youtube": "📺",
        "pinterest": "📌",
        "instagram": "📷",
        "facebook": "📘",
        "twitter": "🐦",
        "linkedin": "💼",
        "blog": "📝"
    }
    return platform_icons.get(platform_name.lower(), "🌐") if platform_name else "🌐"

def get_source_title(source_type, source_id):
    from app.core.extensions import db
    from app.domains.content.models import Content
    from app.domains.item.models import Item
    
    if source_type == "content":
        asset = db.session.get(Content, source_id)
        if asset:
            return asset.title or f"Content #{asset.id}"
    elif source_type == "item":
        asset = db.session.get(Item, source_id)
        if asset:
            return asset.name or f"Item #{asset.id}"
            
    return f"Unknown {source_type}"
