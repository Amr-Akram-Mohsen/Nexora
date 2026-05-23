"""Item serialization for templates and APIs."""

from app.domains.serializers import serialize_model


def _serialize_store_link(link):
    if not link or not link.is_active:
        return None
    return {
        "id": link.id,
        "affiliate_url": link.affiliate_url,
        "price": float(link.price) if link.price is not None else None,
        "old_price": float(link.old_price) if link.old_price is not None else None,
        "currency": link.currency,
        "store": {
            "name": link.store.name,
            "logo_url": link.store.logo_url,
            "slug": link.store.slug,
        }
        if link.store
        else None,
    }


def _serialize_store_links(links):
    return [row for row in (_serialize_store_link(link) for link in links) if row]


def serialize_item(item):
    if not item:
        return None

    default_variant = item.default_variant
    serialized_store_links = (
        _serialize_store_links(default_variant.store_links) if default_variant else []
    )

    return {
        "id": item.id,
        "name": item.name,
        "slug": item.slug,
        "type": item.item_type,
        "item_type": item.item_type,
        "card_type": item.card_type,
        "brand": serialize_model(item.brand),
        "category": serialize_model(item.category),
        "image": item.image_url,
        "image_url": item.image_url,
        "price": float(item.price) if item.price is not None else None,
        "min_price": float(item.min_price) if item.min_price is not None else None,
        "has_variants": item.has_variants,
        "default_variant": {
            "id": default_variant.id,
            "sku": getattr(default_variant, "sku", None),
            "price": float(default_variant.price)
            if default_variant.price is not None
            else None,
        }
        if default_variant
        else None,
        "variant_data": item.variant_payload,
        "variant_groups": item.variant_groups,
        "store_links": serialized_store_links,
        "stores": [
            {
                "name": link["store"]["name"] if link["store"] else "",
                "slug": link["store"]["slug"] if link["store"] else "",
                "price": link["price"],
                "currency": link["currency"],
            }
            for link in serialized_store_links
        ],
        "rating": item.rating,
        "review_count": item.review_count,
        "view_count": item.view_count,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "badges": item.pick_keys(item.searchable_attributes, ["badge", "tag"])
        if item.searchable_attributes
        else None,
    }


def serialize_item_variant(v, *, include_store_links=False):
    data = {
        "id": v.id,
        "title": v.title,
        "sku": v.sku,
        "attributes": v.attributes or {},
        "is_default": v.is_default,
        "price": float(v.price) if v.price is not None else None,
        "old_price": float(v.old_price) if v.old_price is not None else None,
        "currency": v.currency,
        "display_name": v.display_name(),
        "images": [
            {"id": img.id, "image_url": img.image_url, "position": img.position}
            for img in (v.images or [])
        ],
    }
    if include_store_links:
        data["store_links"] = _serialize_store_links(v.store_links)
    return data


def serialize_item_detail(item):
    if not item:
        return None

    data = serialize_item(item)
    structured = item.structured_details
    groups = structured.get("groups") if structured else None

    data.update(
        {
            "images": [
                {
                    "id": img.id,
                    "image_url": img.image_url,
                    "position": img.position,
                }
                for img in item.images
            ],
            "variants": [
                serialize_item_variant(
                    v,
                    include_store_links=v.is_default,
                )
                for v in item.variants
            ],
            "structured_details": structured,
            "quick_details": item.quick_details,
            # "variant_data": item.variant_payload,
            # Compare page and legacy callers; same payload as structured groups.
            "full_details": groups if isinstance(groups, dict) else item.full_details,
        }
    )
    return data
