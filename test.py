# from app.domains.content.models import Article, Video

# # Check Video Integrity
# v = Video.query.order_by(Video.created_at.desc()).first()
# print(f"Video: {v.title} | Channel: {v.channel_name} | Platform: {v.platform}")

# # Check Article Integrity
# a = Article.query.order_by(Article.created_at.desc()).first()
# print(f"Article: {a.title} | URL: {a.url}")
# print(f"Content HTML length: {len(a.content_html) if a.content_html else 0}")
# print(f"Legacy Content length: {len(a.body) if a.body else 0}")
# print(f"Quality Score: {a.quality_score}")
# print(f"Published: {a.published_at}")
print('hello world!')