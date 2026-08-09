def serialize_item_detail_modal(product):
    """
    Serializes a product and its store links with price spread calculation for the admin inspect modal.
    """
    if not product:
        return None

    store_links_data = []
    for v in product.variants:
        for lnk in v.store_links:
            store_links_data.append({
                "store_name":        lnk.store.name if lnk.store else "—",
                "affiliate_network": lnk.store.affiliate_network if lnk.store else "—",
                "program_name":      lnk.program_name or "—",
                "affiliate_url":     lnk.affiliate_url or "—",
                "original_url":      lnk.original_url or "—",
                "price":             float(lnk.price) if lnk.price is not None else None,
                "currency":          lnk.currency,
                "availability":      lnk.availability,
                "is_active":         lnk.is_active,
                "metadata":          lnk.network_metadata or {},
            })

    prices = [p["price"] for p in store_links_data if p["price"] is not None and p["is_active"]]
    price_spread = None
    if prices:
        min_p = min(prices)
        max_p = max(prices)
        delta_pct = ((max_p - min_p) / min_p * 100) if min_p > 0 else 0
        price_spread = {
            "min": round(min_p, 2),
            "max": round(max_p, 2),
            "delta_percentage": round(delta_pct, 1)
        }

    return {
        "id":          product.id,
        "name":        product.name,
        "product_type":   product.product_type or "—",
        "brand":       product.brand.name if product.brand else "—",
        "category":    product.category.name if product.category else "—",
        "source_name": product.source.name if product.source else "—",
        "source_slug": product.source.slug if product.source else None,
        "source_type": product.source_type or "—",
        "store_links": store_links_data,
        "price_spread": price_spread
    }
