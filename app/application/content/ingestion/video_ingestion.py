from app.domains.content.models import Video
from .base import generic_ingest
from app.integrations.content.article_utils.cleaner import clean_video_data

def create_video_model(data):
    if not data.get("external_id"):
        raise ValueError("Missing external_id for video")
    
    return Video(
        title=data.get("title", "Untitled Video"),
        description=data.get("description", ""),
        external_id=data["external_id"],
        platform=data.get("platform", "youtube"),
        thumbnail_url=data.get("thumbnail_url"),
        channel_name=data.get("channel_name")
    )

def ingest_video(session, raw_data):
    cleaned = clean_video_data(raw_data)
    if not cleaned:
        return None, False

    return generic_ingest(
        session,
        object_type="video",
        raw_data=cleaned,
        model_class=Video,
        factory_func=create_video_model
    )
