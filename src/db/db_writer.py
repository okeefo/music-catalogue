import sqlite3
from typing import Optional
from log_config import get_logger

logger = get_logger(__name__)


class MusicCatalogDBWriter:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = self.__connect()

    def __connect(self):
        try:
            connection = sqlite3.connect(self.db_path)
            logger.info("Connected to SQLite database (writer).")
            return connection
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database: {e}")
        return None

    def ensure_track_meta_data_table(self):
        """
        Ensures the track_meta_data table exists.
        """
        query = """
        CREATE TABLE IF NOT EXISTS track_meta_data (
            id INTEGER PRIMARY KEY REFERENCES track_formats(id),
            waveform_data BLOB
        )
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            self.connection.commit()
            cursor.close()
            logger.info("Ensured track_meta_data table exists.")
        except Exception as e:
            logger.error(f"Failed to create track_meta_data table: {e}")

    def write_waveform_data(self, track_file_id: int, waveform_data: bytes) -> bool:
        """
        Inserts or updates waveform data for a given track_file_id.
        """
        self.ensure_track_meta_data_table()
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                INSERT INTO track_meta_data (id, waveform_data)
                VALUES (?, ?)
                ON CONFLICT(id) DO UPDATE SET waveform_data=excluded.waveform_data
                """,
                (track_file_id, waveform_data),
            )
            self.connection.commit()
            cursor.close()
            logger.info(f"Waveform data written for track_file_id={track_file_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to write waveform data: {e}")
            return False

    def close(self):
        if self.connection:
            self.connection.close()
            logger.info("SQLite connection (writer) closed.")
