from sqlalchemy import func, select, case as sa_case
from app.domains.product.models import Product
from app.domains.product.service import get_item_card_load_options


def build_item_search_vector(product):
    return (
        func.setweight(
            func.to_tsvector(
                "english",
                func.coalesce(
                    product.name,
                    ""
                )
            ),
            "A"
        ).op("||")(
            func.setweight(
                func.to_tsvector(
                    "english",
                    func.coalesce(
                        product.description,
                        ""
                    )
                ),
                "B"
            )
        ).op("||")(
            func.setweight(
                func.to_tsvector(
                    "english",
                    func.coalesce(
                        product.search_text,
                        ""
                    )
                ),
                "C"
            )
        )
    )


def populate_item_search_fields(product):

    brand_name = (
        product.brand.name
        if product.brand
        else ""
    )

    category_name = (
        product.category.name
        if product.category
        else ""
    )

    # Attribute facet names from the many-to-many relationship
    attribute_names = ""
    if hasattr(product, "attributes") and product.attributes:
        attribute_names = " ".join(
            attr.name for attr in product.attributes if attr.name
        )

    # Extract searchable_attributes JSON field (e.g. {"storage": "512GB", "RAM": "8GB"})
    # Both keys and values are included so queries like "512GB" or "8GB RAM" match.
    spec_text = ""
    if product.searchable_attributes and isinstance(product.searchable_attributes, dict):
        parts = []
        for k, v in product.searchable_attributes.items():
            if k:
                parts.append(str(k))
            if v:
                parts.append(str(v))
        spec_text = " ".join(parts)

    product.search_text = " ".join(
        filter(
            None,
            [
                product.name,
                product.description,

                brand_name,
                category_name,

                attribute_names,
                spec_text,

                product.product_type
            ]
        )
    )

    product.search_vector = build_item_search_vector(product)


def get_search_items(
    query_str,
    limit=80,
    session=None
):
    if session is None:
        from app.core.extensions import db
        session = db.session

    query_str = (query_str or "").strip()
    if not query_str:
        return []

    # websearch_to_tsquery handles operators (AND, OR, phrases, negation).
    # coalesce/nullif ensures we fall back to plainto_tsquery at the SQL level
    # when the web query would produce an empty tsquery (e.g. bare "-" input).
    web_q = func.websearch_to_tsquery("english", query_str)
    plain_q = func.plainto_tsquery("english", query_str)
    empty_q = func.to_tsquery("")
    search_query = func.coalesce(func.nullif(web_q, empty_q), plain_q)

    rank = func.ts_rank_cd(
        Product.search_vector,
        search_query
    )

    # Title prefix-match boost: products whose name starts with the raw query
    # string appear above purely ts_rank-ranked matches.
    title_boost = sa_case(
        (func.lower(Product.name).startswith(query_str.lower()), 0),
        else_=1
    )

    stmt = (
        select(Product)
        .options(*get_item_card_load_options())
        .where(
            Product.search_vector.op("@@")(search_query),
            Product.ingestion_status.in_(["published", "ready"])
        )
        .order_by(
            title_boost,
            rank.desc(),
            Product.review_count.desc(),
            Product.view_count.desc(),
            Product.created_at.desc()
        )
    )

    if limit:
        stmt = stmt.limit(limit)

    return session.execute(stmt).scalars().all()
