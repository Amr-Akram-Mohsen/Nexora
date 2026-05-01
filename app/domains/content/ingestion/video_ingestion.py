from ..models import Video
from .base import generic_ingest

def create_video_model(raw_data):
    return Video(
        title=raw_data["title"],
        description=raw_data["description"],
        external_id=raw_data["external_id"],
        platform=raw_data.get("platform", "youtube"),
        thumbnail_url=raw_data.get("image_url"), # Standardized in cleaner
        channel_name=raw_data.get("source_name")  # Standardized in cleaner
    )

def ingest_video(session, raw_data):
    return generic_ingest(
        session,
        object_type="video",
        raw_data=raw_data,
        model_class=Video,
        factory_func=create_video_model
    )
