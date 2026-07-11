import sys
from app.core import create_app
from app.core.extensions import db
from app.domains.content.models import Article, Content

app = create_app()
with app.app_context():
    article = Article.query.join(Content, Content.object_id == Article.id).filter(Content.is_published == True).order_by(Content.published_at.desc()).first()
    
    if article:
        print(f"Article ID: {article.id}")
        print(f"content_blocks: {article.content_blocks}")
        print(f"content_html: {article.content_html}")
        print(f"content_text length: {len(article.content_text) if article.content_text else 0}")
        try:
            paragraphs = article.formatted_paragraphs
            print(f"formatted_paragraphs length: {len(paragraphs)}")
            if paragraphs:
                print(f"First para: {paragraphs[0][:100]}")
        except Exception as e:
            print(f"Exception in formatted_paragraphs: {e}")
    else:
        print("No article found")
