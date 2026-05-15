import os
import sqlite3
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config_manager import ConfigurationManager
from log_config import get_logger

logger = get_logger(__name__)

_DEFAULT_DB_NAME = "music-catalog-v1"


def setup_database():
    logger.info("Setting up the database: reading config.ini and creating tables if they do not exist.")
    cfg = ConfigurationManager()

    if not cfg.db_location:
        default_location = os.path.join(os.path.dirname(os.path.realpath(__file__)), "db")
        logger.info(f"db.location not set in config.ini — using default: {default_location}")
        cfg.set("db", "location", default_location)

    if not cfg.get("db", "name"):
        logger.info(f"db.name not set in config.ini — using default: {_DEFAULT_DB_NAME}")
        cfg.set("db", "name", _DEFAULT_DB_NAME)

    if not cfg.db_location or not cfg.get("db", "name"):
        cfg.save()

    db_path = cfg.db_path
    logger.info(f"Connecting to database: {db_path}")

    with sqlite3.connect(db_path) as conn:
        __create_db_tables(
            conn,
            """
            CREATE TABLE IF NOT EXISTS release
            (
                release_id       INTEGER PRIMARY KEY,
                name             TEXT,
                artist           TEXT,
                label            TEXT,
                catalogue_number TEXT,
                media            TEXT,
                style            TEXT,
                genre            TEXT,
                date             TEXT,
                country          TEXT,
                url              TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS tracks
            (
                release_id   INTEGER,
                track_number INTEGER,
                name         TEXT,
                artist       TEXT,
                side         TEXT,
                duration     INTEGER,
                FOREIGN KEY(release_id) REFERENCES release(release_id),
                PRIMARY KEY(release_id, track_number)
            )
            """,
        )

        __create_db_tables(
            conn,
            """
            CREATE TABLE IF NOT EXISTS media_types
            (
                id     INTEGER PRIMARY KEY,
                format TEXT UNIQUE
            )
            """,
            "INSERT OR IGNORE INTO media_types (format) VALUES ('WAV')",
        )

        conn.execute("INSERT OR IGNORE INTO media_types (format) VALUES ('MP3')")
        conn.execute("INSERT OR IGNORE INTO media_types (format) VALUES ('VINYL')")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS _vinyl_copies
            (
                release_id INTEGER PRIMARY KEY,
                copies     INTEGER
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS digital_media
            (
                release_id    INTEGER,
                track_name    TEXT,
                track_artist  TEXT,
                track_number  INTEGER,
                file_path     TEXT,
                file_name     TEXT,
                file_location TEXT,
                file_size     INTEGER,
                media_type    INTEGER,
                FOREIGN KEY(release_id) REFERENCES release(release_id),
                PRIMARY KEY(release_id, track_number)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_release_id  ON digital_media(release_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_artist      ON digital_media(track_artist)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_track_name  ON digital_media(track_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_media_type  ON digital_media(media_type)")

        conn.commit()


def __create_db_tables(conn: sqlite3.Connection, *statements: str) -> sqlite3.Cursor:
    cursor = conn.cursor()
    for stmt in statements:
        cursor.execute(stmt)
    return cursor


if __name__ == "__main__":
    confirm = input("Are you sure you want to setup the database? (yes/no): ")
    if confirm.lower() == "yes":
        setup_database()
    else:
        print("Database setup cancelled.")
