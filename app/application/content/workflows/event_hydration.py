import logging
from app.core.extensions import db
from app.domains.content.models.event import Event
from app.integrations.content.core.api_fetchers import fetch_newsapi_event
from app.integrations.content.core.fetchers_mappers import map_newsapi_event

from flask import current_app

def get_logger():
    return current_app.logger

def run_event_hydration(limit=20):
    """
    Finds incomplete Events in the database and enriches them via NewsAPI AI.
    """
    logger = current_app.logger
    logger.info(f"Starting event hydration worker (limit={limit})...")
    
    # Query events that have an external_uri but are missing summary or title
    events = db.session.query(Event).filter(
        Event.external_uri.isnot(None),
        (Event.summary.is_(None) | Event.title.is_(None) | Event.image_url.is_(None))
    ).limit(limit).all()

    if not events:
        logger.info("No incomplete events found for hydration.")
        return {"hydrated": 0, "skipped": 0}

    hydrated_count = 0
    skipped_count = 0

    for event in events:
        logger.info(f"Hydrating event: {event.external_uri}")
        try:
            raw_data = fetch_newsapi_event(event.external_uri)
            if not raw_data:
                logger.warning(f"No data returned for event {event.external_uri}")
                skipped_count += 1
                continue

            mapped_data = map_newsapi_event(raw_data)
            if not mapped_data:
                logger.warning(f"Failed to map data for event {event.external_uri}")
                skipped_count += 1
                continue

            # Update the Event model
            changed = False
            if mapped_data.get("title") and not event.title:
                event.title = mapped_data["title"]
                changed = True
            if mapped_data.get("summary") and not event.summary:
                event.summary = mapped_data["summary"]
                changed = True
            if mapped_data.get("image_url") and not event.image_url:
                event.image_url = mapped_data["image_url"]
                changed = True
            if mapped_data.get("event_type") and not event.event_type:
                event.event_type = mapped_data["event_type"]
                changed = True
            if mapped_data.get("event_date") and not event.event_date:
                event.event_date = mapped_data["event_date"]
                changed = True
            if mapped_data.get("importance") and not event.importance:
                event.importance = mapped_data["importance"]
                changed = True
            
            # Update article count if it's higher
            ac = mapped_data.get("article_count")
            if ac and (event.article_count is None or ac > event.article_count):
                event.article_count = ac
                changed = True

            if changed:
                db.session.add(event)
                db.session.commit()
                hydrated_count += 1
                logger.info(f"Successfully hydrated event {event.external_uri}")
            else:
                skipped_count += 1
                logger.info(f"No missing fields to update for event {event.external_uri}")

        except Exception as e:
            logger.error(f"Error hydrating event {event.external_uri}: {e}")
            db.session.rollback()
            skipped_count += 1

    logger.info(f"Event hydration complete. Hydrated: {hydrated_count}, Skipped: {skipped_count}")
    return {"hydrated": hydrated_count, "skipped": skipped_count}
