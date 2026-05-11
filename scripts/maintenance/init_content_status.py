from main import app
from dotenv import load_dotenv
load_dotenv()
from app.core.extensions import db
from app.domains.content.models.article import Article
from app.domains.content.models.video import Video
from app.domains.content.models.post import Post

def initialize_content_status():
    with app.app_context():
        print(f"Using database: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print("Initializing Article status...")
        # Mark articles with content as published
        articles = Article.query.all()
        for a in articles:
            if a.is_published is None:
                # If it has a body or content_text, it's likely already scraped/good
                if (a.content_text and len(a.content_text) > 200) or (a.body and len(a.body) > 200):
                    a.status = "complete"
                    a.is_published = True
                else:
                    a.status = "pending"
                    a.is_published = False
        
        print("Initializing Video status...")
        Video.query.update({Video.is_published: True})
        
        print("Initializing Post status...")
        Post.query.update({Post.is_published: True})
        
        db.session.commit()
        print("Initialization complete.")

if __name__ == "__main__":
    initialize_content_status()
