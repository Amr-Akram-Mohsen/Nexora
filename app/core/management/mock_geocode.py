import random
from app.core.extensions import db
from app.domains.taxonomy.models import Location

def seed_mock_coordinates():
    # Common locations and rough coords
    known_locs = {
        "united states": (37.0902, -95.7129),
        "uk": (55.3781, -3.4360),
        "london": (51.5074, -0.1278),
        "paris": (48.8566, 2.3522),
        "france": (46.2276, 2.2137),
        "germany": (51.1657, 10.4515),
        "japan": (36.2048, 138.2529),
        "tokyo": (35.6762, 139.6503),
        "india": (20.5937, 78.9629),
        "china": (35.8617, 104.1954),
        "australia": (-25.2744, 133.7751),
        "canada": (56.1304, -106.3468),
        "brazil": (-14.2350, -51.9253),
        "russia": (61.5240, 105.3188),
        "egypt": (26.8206, 30.8025),
        "south africa": (-30.5595, 22.9375),
    }

    locations = Location.query.all()
    count = 0
    for loc in locations:
        name_lower = loc.name.lower()
        if name_lower in known_locs:
            loc.latitude = known_locs[name_lower][0]
            loc.longitude = known_locs[name_lower][1]
            count += 1
        else:
            # Assign random coordinates to 10% of other locations just to populate the globe
            if random.random() < 0.1:
                loc.latitude = random.uniform(-60, 60)
                loc.longitude = random.uniform(-180, 180)
                count += 1

    db.session.commit()
    print(f"Mocked {count} coordinates for testing.")

if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
    from main import app
    with app.app_context():
        seed_mock_coordinates()
