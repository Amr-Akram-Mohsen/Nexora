import sys
from app.core import create_app
from app.core.extensions import db
from app.domains.content.models import Article, Content

app = create_app()
with app.app_context():
    # Find any article that is published and has content_text
    article = Article.query.join(Content, Content.object_id == Article.id).filter(Content.is_published == True, Article.content_text != None).first()
    
    if article and article.content_text:
        text = article.content_text
        print(f"Article ID: {article.id}")
        print(f"Length: {len(text)}")
        print(f"Contains \\n: {'\\n' in text}")
        print(f"Contains \\r: {'\\r' in text}")
        print("--- Text Sample (first 1000 chars) ---")
        print(repr(text[:1000]))
    else:
        print("No published article with content_text found.")
