from sqlalchemy import func
from app.domains.item.models import Item
from app.domains.item.service import get_item_card_load_options

def build_item_search_vector(item):
    return (
        func.setweight(
            func.to_tsvector(
                "english",
                func.coalesce(
                    item.name,
                    ""
                )
            ),
            "A"
        ).op("||")(
            func.setweight(
                func.to_tsvector(
                    "english",
                    func.coalesce(
                        item.description,
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
                        item.search_text,
                        ""
                    )
                ),
                "C"
            )
        )
    )

def populate_item_search_fields(item):

    brand_name = (
        item.brand.name
        if item.brand
        else ""
    )

    category_name = (
        item.category.name
        if item.category
        else ""
    )

    # attribute_names = " ".join(
    #     attr.name
    #     for attr in item.searchable_attributes
    # )
    attribute_names = ""

    item.search_text = " ".join(
        filter(
            None,
            [
                item.name,
                item.description,

                brand_name,
                category_name,

                attribute_names,

                item.item_type
            ]
        )
    )

    item.search_vector = build_item_search_vector(item)

from sqlalchemy import select

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
        Item.search_vector,
        search_query
    )

    stmt = (
        select(Item)
        .options(*get_item_card_load_options())
        .where(
            Item.search_vector.op("@@")(search_query)
        )
        .order_by(
            rank.desc(),
            Item.review_count.desc(),
            Item.view_count.desc(),
            Item.created_at.desc()
        )
    )
    
    if limit:
        stmt = stmt.limit(limit)

    return session.execute(stmt).scalars().all()

