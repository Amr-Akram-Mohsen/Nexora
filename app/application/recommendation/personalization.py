from app.application.interaction.get_history import get_reading_history_workflow
from app.application.interaction.get_saved import get_saved_articles_workflow, get_saved_products_workflow
from app.domains.content.service.query.trending import get_popular_contents
from app.domains.product.service.query import get_popular_items
from app.core.extensions import db

def get_personalized_feed_workflow(user_id, limit=12):
    """
    Analyzes the user's recent history and saved products to extract
    dominant taxonomy elements (categories/brands).
    Returns a personalized list of recommended products.
    """
    
    # 1. Fetch History and Saves
    history = get_reading_history_workflow(user_id, limit=20)
    saved_articles = get_saved_articles_workflow(user_id)
    saved_products = get_saved_products_workflow(user_id)
    
    # Combine interactions
    all_interactions = history + saved_articles + saved_products
    
    if not all_interactions:
        return []

    # 2. Extract signals (Taxonomies) and Seen IDs
    category_slugs = set()
    brand_slugs = set()
    seen_content_ids = set()
    seen_product_ids = set()
    
    for product in all_interactions:
        domain_type = product.get("domain_type")
        product_id = product.get("id")
        
        if domain_type == "content":
            seen_content_ids.add(product_id)
        else:
            seen_product_ids.add(product_id)
            
        # Extract Category
        cat = product.get("category")
        if isinstance(cat, dict) and "slug" in cat:
            category_slugs.add(cat["slug"])
            
        # Extract Brand (Product structure)
        brand = product.get("brand")
        if isinstance(brand, dict) and "slug" in brand:
            brand_slugs.add(brand["slug"])
            
        # Extract Brands (Content structure)
        brands = product.get("brands")
        if isinstance(brands, list):
            for b in brands:
                if isinstance(b, dict) and "slug" in b:
                    brand_slugs.add(b["slug"])
                
    # If no taxonomies found, fallback to empty list
    if not category_slugs and not brand_slugs:
        return []
        
    # 3. Query based on signals
    recommended = []
    
    # Try fetching content recommendations (limit to half the budget)
    content_limit = limit // 2
    content_recs = []
    
    if category_slugs:
        cat_recs = get_popular_contents(
            category_slugs=tuple(category_slugs),
            limit=content_limit + len(seen_content_ids),
            session=db.session
        )
        content_recs.extend(cat_recs)
        
    if brand_slugs and len(content_recs) < (content_limit + len(seen_content_ids)):
        brand_recs = get_popular_contents(
            brand_slugs=tuple(brand_slugs),
            limit=content_limit + len(seen_content_ids),
            session=db.session
        )
        # Avoid duplicates from the category query
        existing_ids = {c["id"] for c in content_recs}
        for b in brand_recs:
            if b["id"] not in existing_ids:
                content_recs.append(b)

    # Filter out seen content
    for c in content_recs:
        if c["id"] not in seen_content_ids:
            recommended.append(c)
            if len(recommended) >= content_limit:
                break
                
    # Try fetching product recommendations
    item_limit = limit - len(recommended)
    if item_limit > 0:
        item_recs = []
        
        if category_slugs:
            cat_items = get_popular_items(
                category_slugs=tuple(category_slugs),
                limit=item_limit + len(seen_product_ids),
                session=db.session
            )
            item_recs.extend(cat_items)
            
        if brand_slugs and len(item_recs) < (item_limit + len(seen_product_ids)):
            brand_items = get_popular_items(
                brand_slugs=tuple(brand_slugs),
                limit=item_limit + len(seen_product_ids),
                session=db.session
            )
            existing_product_ids = {i["id"] for i in item_recs}
            for b in brand_items:
                if b["id"] not in existing_product_ids:
                    item_recs.append(b)
        
        # Filter out seen products
        added_items = 0
        for i in item_recs:
            if i["id"] not in seen_product_ids:
                recommended.append(i)
                added_items += 1
                if added_items >= item_limit:
                    break

    # We shuffle or leave as is (content first, then products). Let's leave as is to group them or let grid handle it.
    return recommended
