from ..models import Post
from .base import generic_ingest

def create_post_model(raw_data):
    return Post(
        title=raw_data.get("title"),
        body=raw_data.get("body") or raw_data.get("description"),
        external_id=raw_data["external_id"],
        platform=raw_data.get("platform", "reddit")
    )

def ingest_post(session, raw_data):
    return generic_ingest(
        session,
        object_type="post",
        raw_data=raw_data,
        model_class=Post,
        factory_func=create_post_model
    )
