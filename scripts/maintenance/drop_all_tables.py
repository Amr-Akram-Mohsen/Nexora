import sys
sys.path.insert(0, '.')
from app.core import create_app
from app.core.extensions import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    with db.engine.connect() as conn:
        # Drop all tables
        conn.execute(text('SET session_replication_role = replica;'))
        result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        tables = [row[0] for row in result]
        for table in tables:
            conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
            print(f'Dropped table: {table}')
        
        # Drop all standalone indexes
        result = conn.execute(text("""
            SELECT indexname FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND indexname NOT LIKE '%_pkey'
        """))
        indexes = [row[0] for row in result]
        for idx in indexes:
            conn.execute(text(f'DROP INDEX IF EXISTS "{idx}" CASCADE'))
            print(f'Dropped index: {idx}')
        
        conn.execute(text('SET session_replication_role = DEFAULT;'))
        conn.commit()
    print('Schema completely clean.')
