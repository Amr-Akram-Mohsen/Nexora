from app.domains.product.service import get_items_by_ids

def get_comparison_data(product_ids):
    """
    Orchestrates data for product comparison.
    """
    if not product_ids:
        return None

    # Limit to 4 products for layout sanity
    product_ids = product_ids[:4]
    products = get_items_by_ids(product_ids, serialize=True)

    if not products:
        return None

    # Extract all possible specification categories from all products being compared
    all_categories = set()
    for product in products:
        full_details = product.get("full_details")
        if full_details:
            all_categories.update(full_details.keys())
    
    return {
        "products": products,
        "all_categories": sorted(list(all_categories))
    }
