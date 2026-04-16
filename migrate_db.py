"""
Database Migration — Add Google Places columns to the rooms table
=================================================================
Run this ONCE after pulling this update to add the six new columns:
  address, latitude, longitude, place_id, google_rating, google_maps_url

Works on SQLite (local dev) and PostgreSQL (Neon production).

Usage:
    python migrate_db.py                          # local .env / SQLite
    DATABASE_URL="postgresql://..." python migrate_db.py   # production
"""

import os
import sys
import logging

logging.disable(logging.CRITICAL)   # silence SQLAlchemy noise

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv()

db_url = os.environ.get("DATABASE_URL", "")
is_postgres = db_url.startswith(("postgres://", "postgresql://"))
env = "production" if is_postgres else "development"

from backend.app import create_app

app = create_app(env)

NEW_COLUMNS = [
    # (column_name, SQL type for SQLite, SQL type for PostgreSQL)
    ("address",         "TEXT",           "TEXT"),
    ("latitude",        "NUMERIC(9,6)",   "NUMERIC(9,6)"),
    ("longitude",       "NUMERIC(9,6)",   "NUMERIC(9,6)"),
    ("place_id",        "VARCHAR(300)",   "VARCHAR(300)"),
    ("google_rating",   "NUMERIC(3,1)",   "NUMERIC(3,1)"),
    ("google_maps_url", "VARCHAR(500)",   "VARCHAR(500)"),
]


from sqlalchemy import text


def column_exists(conn, table: str, column: str) -> bool:
    if is_postgres:
        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c"
            ),
            {"t": table, "c": column},
        )
        return len(result.fetchall()) > 0
    else:
        result = conn.execute(text(f"PRAGMA table_info({table})"))
        cols = [row[1] for row in result.fetchall()]
        return column in cols


with app.app_context():
    from backend.database import db

    with db.engine.connect() as conn:
        added   = []
        skipped = []

        for col_name, sqlite_type, pg_type in NEW_COLUMNS:
            if column_exists(conn, "rooms", col_name):
                skipped.append(col_name)
                continue

            sql_type = pg_type if is_postgres else sqlite_type
            try:
                conn.execute(text(f"ALTER TABLE rooms ADD COLUMN {col_name} {sql_type}"))
                added.append(col_name)
            except Exception as exc:
                print(f"  ERROR adding {col_name}: {exc}")

        conn.commit()

    if added:
        print(f"Migration complete. Added columns: {', '.join(added)}")
    if skipped:
        print(f"Already existed (skipped): {', '.join(skipped)}")
    if not added and not skipped:
        print("No columns processed — check table name.")
