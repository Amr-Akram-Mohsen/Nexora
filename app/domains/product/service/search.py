from sqlalchemy import func, select
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

    # attribute_names = " ".join(
    #     attr.name
    #     for attr in product.searchable_attributes
    # )
    attribute_names = ""

    product.search_text = " ".join(
        filter(
            None,
            [
                product.name,
                product.description,

                brand_name,
                category_name,

                attribute_names,

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

    search_query = func.websearch_to_tsquery(
        "english",
        query_str
    )

    rank = func.ts_rank_cd(
        Product.search_vector,
        search_query
    )

    stmt = (
        select(Product)
        .options(*get_item_card_load_options())
        .where(
            Product.search_vector.op("@@")(search_query)
        )
        .order_by(
            rank.desc(),
            Product.review_count.desc(),
            Product.view_count.desc(),
            Product.created_at.desc()
        )
    )
    
    if limit:
        stmt = stmt.limit(limit)

    return session.execute(stmt).scalars().all()

