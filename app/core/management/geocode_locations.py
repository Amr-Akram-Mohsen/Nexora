import time
import requests
from app.core.extensions import db
from app.domains.taxonomy.models import Location
import logging

logger = logging.getLogger(__name__)

def hydrate_locations():
    """
    Iterates through all locations missing coordinates and fetches them via Nominatim API.
    """
    locations = Location.query.filter((Location.latitude == None) | (Location.longitude == None)).all()
    total = len(locations)
    
    if total == 0:
        logger.info("All locations are already geocoded.")
        return

    logger.info(f"Starting geocoding for {total} locations...")

    headers = {
        "User-Agent": "Nexora/1.0 (contact@nexora.com)"
    }

    success = 0
    failed = 0

    for i, loc in enumerate(locations):
        query = f"{loc.name}"
        if loc.country_name and loc.country_name.lower() not in query.lower():
            query = f"{loc.name}, {loc.country_name}"

        try:
            # Nominatim Search API
            url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(query)}&format=json&limit=1"
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    loc.latitude = float(data[0]["lat"])
                    loc.longitude = float(data[0]["lon"])
                    success += 1
                else:
                    failed += 1
            else:
                failed += 1
                
        except Exception as e:
            logger.error(f"Error geocoding {loc.name}: {e}")
            failed += 1
            
        # Commit every 50 records to save progress
        if i % 50 == 0:
            db.session.commit()
            
        # Respect Nominatim's 1 request/sec policy
        time.sleep(1)

    db.session.commit()
    logger.info(f"Geocoding complete. Success: {success}, Failed: {failed}")

if __name__ == "__main__":
    import sys
    import os
    # Ensure app context
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
    from main import app
    with app.app_context():
        # Setup basic logging to stdout
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        hydrate_locations()
