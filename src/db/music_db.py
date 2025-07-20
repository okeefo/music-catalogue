import sqlite3
from dataclasses import dataclass

from log_config import get_logger
from typing import Dict, Optional, Any

logger = get_logger(__name__)

@dataclass
class Release:
    release_id: int
    date: str
    country: str
    website: str
    album_id: int
    album_title: str
    album_artist_id: int
    album_artist_name: str
    catalog_id: int
    catalog_number: str
    label_id: int
    label_name: str

    def __str__(self):
         return f"{self.catalog_number} - {self.album_title}"

@dataclass
class Track:
    track_id: int
    catalog_number: str
    label: str
    album_title: str
    disc_number: int
    track_artist: str
    track_title: str
    format: str
    track_number: int
    discogs_id: int
    year: int
    country: str
    discogs_url: str
    album_artist: str
    file_location: str
    style: str
    genre: str

class MusicCatalogDB:
    def __init__(self, db_path: str) -> None:
        """
        Initializes the MusicCatalogDB instance.

        Args:
            db_path (str): Path to the SQLite database file.
        """
        self.db_path = db_path
        self._tracks_cache: Dict[int, Dict[str, Any]] = {}
        self._releases_cache: Dict[int, Release] = {}
        self.connection: Optional[sqlite3.Connection] = self.__connect()

    def __connect(self):
        """Establishes an SQLite connection and keeps it as an instance attribute."""
        try:
            connection = sqlite3.connect(self.db_path)
            logger.info("Connected to SQLite database.")
            return connection
        except sqlite3.Error as e:
            logger.info(f"Error connecting to database: {e}")
        return None

    # Python
    def load(self) -> bool:
        """
        Loads the database and initializes the tracks cache.
        Returns True if successful, False otherwise.
        """
        connection = self.__connect()
        if connection is None:
            return False
        try:
            result = self.__load_tracks(connection)
            if not result:
                logger.error("Failed to load tracks from the database.")
                return False

            logger.info(f"Loaded {len(self._tracks_cache)} tracks from the database.")
            result = self.__load_releases(connection)
            if not result:
                logger.error("Failed to load releases from the database.")
                return False

            logger.info(f"Loaded {len(self._releases_cache)} releases from the database.")
            return True
        except Exception as e:
            logger.error(f"Failed to load tracks adn releases: {e}")
            return False
        finally:
            connection.close()

    def __load_tracks(self,  conn: sqlite3.Connection) -> bool:
        """
        Loads tracks from the uber tracks view into the cache.
        Returns a dictionary where each key is the track_id.
        """
        query = "SELECT * FROM uber_tracks"
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        # Load tracks into cache, keyed by track_id
        cache = self._tracks_cache
        for row in rows:
            track = {
                "track_id": row[0],
                "catalog_number": row[1],
                "label": row[2],
                "album_title": row[3],
                "disc_number": row[4],
                "track_artist": row[5],
                "track_title": row[6],
                "format": row[7],
                "track_number": row[8],
                "discogs_id": row[9],
                "year": row[10],
                "country": row[11],
                "discogs_url": row[12],
                "album_artist": row[13],
                "file_location": row[14],
                "style": row[15],
                "genre": row[16]
            }
            # Use track_id as key in the cache
            cache[track["track_id"]] = track

        cursor.close()
        return True

    # Python
    def __load_releases(self,  conn: sqlite3.Connection) -> bool:
        """
        Load full releases from the database and return a cache indexed by discogs_id.
        :param conn: Database connection object.
        :return: Dictionary with discogs_id as keys and release information as values.
        """
        query = "SELECT * FROM full_releases"
        cache = self._releases_cache
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        for row in rows:
            discogs_id = row["discogs_id"]
            release = Release(
                release_id=row["release_id"],
                date=row["date"],
                country=row["country"],
                website=row["website"],
                album_id=row["album_id"],
                album_title=row["album_title"],
                album_artist_id=row["album_artist_id"],
                album_artist_name=row["album_artist_name"],
                catalog_id=row["catalog_id"],
                catalog_number=row["catalog_number"],
                label_id=row["label_id"],
                label_name=row["label_name"],
            )
            cache[discogs_id] = release
        cursor.close()
        return True

    def get_releases(self) -> Dict[int, Release]:
        """
        Returns the cached releases if already loaded, otherwise loads them.

        Returns:
            Cached list of releases.
        """
        if self._releases_cache is None:
            self.load_releases()
        return self._releases_cache

    def count_tracks(self) -> int:
        """
        Counts the number of tracks in the cache.

        Returns:
            int: Number of tracks.
        """
        if self._tracks_cache is None:
            return 0
        return len(self._tracks_cache)

    def count_releases(self) -> int:
        """
        Counts the number of releases in the cache.

        Returns:
            int: Number of releases.
        """
        if self._tracks_cache is None:
            return 0
        return len(self._releases_cache)

    def get_tracks(self)-> Dict[int, Track]:
        """
        Returns the cached tracks if already loaded, otherwise loads them.

        Returns:
            Cached list of tracks.
        """
        if self._tracks_cache is None:
            return self.load_tracks()
        return self._tracks_cache

    def close(self):
        """Closes the SQLite connection."""
        if self.connection:
            self.connection.close()
            print("SQLite connection closed.")


# Dummy execution for testing purposes
if __name__ == "__main__":
    db = MusicCatalogDB("music_catalog.db")
    tracks = db.load_tracks()
    print("Loaded tracks:", tracks)
    db.close()
