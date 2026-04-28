from .article_ingestion import ingest_article
from .video_ingestion import ingest_video
from .post_ingestion import ingest_post

def ingest_content(session, *, object_type, raw_data):
    if object_type == "article":
        return ingest_article(session, raw_data)

    elif object_type == "video":
        return ingest_video(session, raw_data)

    elif object_type == "post":
        return ingest_post(session, raw_data)

    return None
