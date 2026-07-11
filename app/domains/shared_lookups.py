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
    from app.domains.product.models import Product
    
    if source_type == "content":
        asset = db.session.get(Content, source_id)
        if asset:
            return asset.title or f"Content #{asset.id}"
    elif source_type == "product":
        asset = db.session.get(Product, source_id)
        if asset:
            return asset.name or f"Product #{asset.id}"
            
    return f"Unknown {source_type}"
