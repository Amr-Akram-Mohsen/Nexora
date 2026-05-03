from app.domains.content.models import Post
from .base import generic_ingest
from app.integrations.content.article_utils.cleaner import clean_post_data

def create_post_model(data):
    return Post(
        title=data.get("title"),
        body=data.get("body"), 
        external_id=data.get("external_id"),
        platform=data.get("platform", "reddit"),
        author=data.get("author"),
        subreddit=data.get("subreddit"),
        upvotes=data.get("upvotes", 0),
        comments_count=data.get("comments_count", 0)
    )

def ingest_post(session, raw_data):
    cleaned = clean_post_data(raw_data)
    if not cleaned:
        return None

    return generic_ingest(
        session,
        object_type="post",
        raw_data=cleaned,
        model_class=Post,
        factory_func=create_post_model
    )
