from sqlalchemy.orm import selectinload, joinedload
from app.domains.content.models import Content

CONTENT_EAGER_LOADS = [
    selectinload(Content.topics),
    selectinload(Content.brands),
    selectinload(Content.section),
    selectinload(Content.category),
]