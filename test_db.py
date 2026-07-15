import os
from main import app
from app.core.extensions import db
from sqlalchemy import text

with app.app_context():
    print("Events with summary:", db.session.execute(text("select count(*) from events where summary is not null")).scalar())
    print("Events with date:", db.session.execute(text("select count(*) from events where event_date is not null")).scalar())
    print("Locations:", db.session.execute(text("select count(*) from locations")).scalar())
    print("Entities with image:", db.session.execute(text("select count(*) from entities where image_url is not null")).scalar())
