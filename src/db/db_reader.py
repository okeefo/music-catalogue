

import sqlite3
from dataclasses import dataclass

from log_config import get_logger
from typing import Dict, Optional, Any

logger = get_logger(__name__)


@dataclass
class Release:
    discogs_id: int
    date: str
    country: str
    title: str
    album_artist_name: str
    catalog_number: str
    label_name: str

    def __str__(self):
        return f"{self.catalog_number} - {self.title}"


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
    file_id: int


@dataclass
class RecordLabel:
    name: str


class MusicCatalogDB_2:
    def __init__(self, db_path: str) -> None:
        """
        Initializes the MusicCatalogDB instance.

        Args:
            db_path (str): Path to the SQLite database file.
        """
        self.db_path = db_path
        self._tracks_cache: Dict[int, Track] = {}
        self._releases_cache: Dict[int, Release] = {}
        self._labels_cache: Dict[str, RecordLabel] = {}
        self._label_to_releases: Dict[str, set] = {}
        self._release_to_tracks: Dict[int, set] = {}
        self._track_list: list[Track] = []  # List to hold all tracks
        #self._files_cache: Dict[int, list[str]] = {}  # Placeholder for file cache
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

            return True
        except Exception as e:
            logger.error(f"Failed to load tracks adn releases: {e}")
            return False
        finally:
            connection.close()

    def __load_tracks(self, conn: sqlite3.Connection) -> bool:
        """
        Loads tracks from the uber tracks view into the cache.
        Returns a dictionary where each key is the track_id.
        """
        query = "SELECT * FROM uber_tracks"
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        # Load tracks into cache, keyed by track_id
        cache = self._tracks_cache
        for row in rows:
            track_id=row["track_id"],
            track = Track(
                track_id=row["track_id"],
                catalog_number=row["catalog_number"],
                label=row["label"],
                album_title=row["album_title"],
                disc_number=row["disc_number"],
                track_artist=row["track_artist"],
                track_title=row["track_title"],
                format=row["format"],
                track_number=row["track_number"],
                discogs_id=row["discogs_id"],
                year=row["year"],
                country=row["country"],
                discogs_url=row["discogs_url"],
                album_artist=row["album_artist"],
                file_location=row["file_location"],
                style=row["style"],
                genre=row["genre"],
                file_id=row["track_file_id"]
            )
            self._tracks_cache[track_id] = track
            self._track_list.append(track)
           
            
            discogs_id = row["discogs_id"]
            if discogs_id not in self._releases_cache:
                release = Release(
                    discogs_id=discogs_id,
                    date=track.year,
                    country=track.country,
                    title=track.album_title,
                    album_artist_name=track.album_artist,
                    catalog_number=track.catalog_number,
                    label_name=track.label
                )
                self._releases_cache[discogs_id] = release
 
            # Label
            label_name = track.label
            if label_name and label_name not in self._labels_cache:
                self._labels_cache[label_name] = RecordLabel(name=label_name)

            # Label -> Releases
            self._label_to_releases.setdefault(label_name, set()).add(discogs_id)
            # Release -> Tracks
            self._release_to_tracks.setdefault(discogs_id, set()).add(track_id)

                
        cursor.close()
        return True
    
     # Retrieval methods:
    def get_all_tracks(self) -> list[Track]:
        return self._track_list
  
    def get_tracks_for_label(self, label_name: str) -> list[Track]:
        track_ids = set()
        for release_id in self._label_to_releases.get(label_name, set()):
            track_ids.update(self._release_to_tracks.get(release_id, set()))
        return [self._tracks_cache[tid] for tid in track_ids]

    def get_releases_for_label(self, label_name: str) -> list[Release]:
        return [self._releases_cache[rid] for rid in self._label_to_releases.get(label_name, set())]

    def get_all_labels(self) -> list[RecordLabel]:
        return list(self._labels_cache.values())
    
    def get_labels_and_releases(self) -> Dict[str, set]:
        """
        Returns a dictionary mapping label names to their releases.
        """
        return self._label_to_releases

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
    
    def get_release_by_id(self, release_id: int) -> Optional[Release]:
        """
        Retrieves a release by its Discogs ID.

        Args:
            discogs_id (int): The Discogs ID of the release.

        Returns:
            Optional[Release]: The Release object if found, None otherwise.
        """
        return self._releases_cache.get(release_id)

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
