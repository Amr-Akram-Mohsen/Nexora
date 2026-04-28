from ..models import Video
from ..content_access import create_content, get_or_create_content

def ingest_video(session, raw_data):
    video = get_or_create_content(
        session,
        object_type="video",
        external_id=raw_data["external_id"],
        obj_factory=lambda: Video(
            title=raw_data["title"],
            description=raw_data["description"],
            external_id=raw_data["external_id"],
            platform=raw_data.get("platform", "youtube")
        )
    )

    content = create_content(
        session,
        obj=video,
        object_type="video",
        published_at=raw_data["published_at"],
        category_id=raw_data["category_id"],
        section_id=raw_data["section_id"]
    )

    session.commit()
    return content
