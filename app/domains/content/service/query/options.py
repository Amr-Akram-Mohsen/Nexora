from sqlalchemy.orm import joinedload, selectinload
from app.domains.content.models import Content

CONTENT_EAGER_LOADS = [
    selectinload(Content.topics),
    selectinload(Content.brands),
    selectinload(Content.section),
    selectinload(Content.category),
]

CONTENT_LIST_EAGER_LOADS = [
    selectinload(Content.topics),
    selectinload(Content.brands),
    joinedload(Content.section),
    joinedload(Content.category),
]


def get_content_detail_loads():
    from app.domains.item.models import Item, ItemVariant, ItemStoreLink

    return [
        *CONTENT_LIST_EAGER_LOADS,
        selectinload(Content.linked_items).joinedload(Item.brand),
        selectinload(Content.linked_items).joinedload(Item.category),
        selectinload(Content.linked_items).selectinload(Item.images),
        selectinload(Content.linked_items)
        .selectinload(Item.variants)
        .selectinload(ItemVariant.store_links)
        .selectinload(ItemStoreLink.store),
    ]
