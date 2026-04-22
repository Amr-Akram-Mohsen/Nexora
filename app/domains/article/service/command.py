from app.core.extensions import db
from app.domains.article.models import Article


def delete_article(id: int) -> bool:
    article = db.session.get(Article, id)

    if not article:
        return False

    db.session.delete(article)
    db.session.commit()
    return True

