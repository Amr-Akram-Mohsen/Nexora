"""
Use SQLAlchemy's create_all() to create all tables with proper FK dependency ordering,
then stamp Alembic so it knows the migration is applied.
"""
import sys
sys.path.insert(0, '.')
from app.core import create_app
from app.core.extensions import db
app = create_app()
with app.app_context():
    print("Creating all tables via SQLAlchemy create_all()...")
    db.create_all()
    print("All tables created successfully.")
    
    # Now stamp alembic so it knows migration is at head
    from flask_migrate import stamp
    stamp()
    print("Alembic stamped at head.")
