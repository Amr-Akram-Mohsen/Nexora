from ..models import Post
from ..content_access import create_content, get_or_create_content

def ingest_post(session, raw_data):
    post = get_or_create_content(
        session,
        object_type="post",
        external_id=raw_data["external_id"],
        obj_factory=lambda: Post(
            title=raw_data.get("title"),
            body=raw_data.get("body"),
            external_id=raw_data["external_id"],
            platform=raw_data.get("platform", "reddit")
        )
    )

    content = create_content(
        session,
        obj=post,
        object_type="post",
        published_at=raw_data["published_at"],
        category_id=raw_data["category_id"],
        section_id=raw_data["section_id"]
    )

    session.commit()
    return content
