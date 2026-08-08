from sqlalchemy.orm import joinedload, selectinload
from app.domains.content.models import Content

CONTENT_EAGER_LOADS = [
    selectinload(Content.content_entities),
    selectinload(Content.section),
    selectinload(Content.category),
    selectinload(Content.locations),
]

CONTENT_LIST_EAGER_LOADS = [
    selectinload(Content.content_entities),
    joinedload(Content.section),
    joinedload(Content.category),
    selectinload(Content.locations),
]


def get_content_detail_loads():
    from app.domains.product.models import Product, ProductVariant, ProductStoreLink

    return [
        *CONTENT_LIST_EAGER_LOADS,
        selectinload(Content.linked_products).joinedload(Product.brand),
        selectinload(Content.linked_products).joinedload(Product.category),
        selectinload(Content.linked_products).selectinload(Product.images),
        selectinload(Content.linked_products)
        .selectinload(Product.variants)
        .selectinload(ProductVariant.store_links)
        .selectinload(ProductStoreLink.store),
    ]
