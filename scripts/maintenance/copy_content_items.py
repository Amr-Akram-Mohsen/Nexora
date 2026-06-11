from sqlalchemy import create_engine, MetaData, Table, text

LOCAL_DB_URL = "postgresql+psycopg2://postgres:amro-nexora@localhost:5432/nexora_db"

SUPABASE_DB_URL = (
    "postgresql+psycopg2://"
    "postgres.hncnnyliivkcxglwimxb:amro-nexora"
    "@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"
    "?sslmode=require"
)

print("Connecting...")

local_engine = create_engine(LOCAL_DB_URL)
remote_engine = create_engine(SUPABASE_DB_URL)

metadata = MetaData()

print("Loading table schema...")

content_items = Table(
    "content_items",
    metadata,
    autoload_with=local_engine,
)

print("Reading local rows...")

with local_engine.connect() as src:
    rows = src.execute(
        text("SELECT * FROM content_items")
    ).mappings().all()

print(f"Found {len(rows)} rows")

with remote_engine.begin() as dst:
    print("Clearing Supabase table...")

    dst.execute(
        text(
            "TRUNCATE TABLE content_items RESTART IDENTITY CASCADE"
        )
    )

    print("Uploading rows...")

    batch_size = 1000

    for i in range(0, len(rows), batch_size):
        batch = [dict(row) for row in rows[i:i + batch_size]]

        dst.execute(
            content_items.insert(),
            batch
        )

        print(
            f"Inserted {min(i + batch_size, len(rows))}/{len(rows)}"
        )

print("Done!")