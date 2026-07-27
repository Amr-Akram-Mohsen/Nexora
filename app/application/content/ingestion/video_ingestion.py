from app.domains.content.models import Video
from .base import generic_ingest
from app.domains.content.service.normalization import normalize_video_data


def _sync_video_comments(video_obj, comments_data):
    if not comments_data:
        return False
        
    from app.domains.content.models.video import VideoComment
    
    changed = False
    # Map existing comments by external_id
    existing_map = {c.external_id: c for c in video_obj.video_comments}
    
    for c_data in comments_data:
        ext_id = c_data["external_id"]
        if ext_id in existing_map:
            # Update
            existing = existing_map[ext_id]
            if (existing.like_count != c_data["like_count"] or 
                existing.reply_count != c_data["reply_count"] or 
                existing.text != c_data["text"]):
                existing.like_count = c_data["like_count"]
                existing.reply_count = c_data["reply_count"]
                existing.text = c_data["text"]
                existing.updated_at = c_data["updated_at"]
                changed = True
        else:
            # Create
            new_comment = VideoComment(
                external_id=ext_id,
                author_name=c_data["author_name"],
                author_channel_id=c_data["author_channel_id"],
                text=c_data["text"],
                like_count=c_data["like_count"],
                reply_count=c_data["reply_count"],
                published_at=c_data["published_at"],
                updated_at=c_data["updated_at"]
            )
            video_obj.video_comments.append(new_comment)
            changed = True
            
    return changed


def create_video_model(data):
    if not data.get("external_id"):
        raise ValueError("Missing external_id for video")

    video = Video(
        title=data.get("title", "Untitled Video"),
        description=data.get("description", ""),
        external_id=data["external_id"],
        platform=data.get("platform", "youtube"),
        thumbnail_url=data.get("thumbnail_url"),
        channel_name=data.get("channel_name"),
        duration_seconds=data.get("duration_seconds"),
        url=data.get("url")
    )
    
    _sync_video_comments(video, data.get("video_comments"))
    return video

def update_video_model(obj, data):
    changed = False
    if data.get("duration_seconds") and obj.duration_seconds != data.get("duration_seconds"):
        obj.duration_seconds = data.get("duration_seconds")
        changed = True
        
    comments_changed = _sync_video_comments(obj, data.get("video_comments"))
    return changed or comments_changed


def ingest_video(session, raw_data):
    cleaned = normalize_video_data(raw_data)
    if not cleaned:
        return None, "skipped"

    return generic_ingest(
        session,
        object_type="video",
        raw_data=cleaned,
        factory_func=create_video_model,
        update_func=update_video_model,
    )
