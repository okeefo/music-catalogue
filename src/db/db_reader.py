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
    def get_waveform_data(self, file_id: int) -> Optional[bytes]:
        """
        Fetch waveform_data BLOB for a given file_id from track_meta_data table.
        Returns the waveform_data as bytes, or None if not found.
        """
        try:
            conn = self.connection or self.__connect()
            cursor = conn.cursor()
            cursor.execute("SELECT waveform_data FROM track_meta_data WHERE id=?", (file_id,))
            row = cursor.fetchone()
            cursor.close()
            if row and row[0]:
                return row[0]
            return None
        except Exception as e:
            logger.error(f"Failed to fetch waveform data for file_id={file_id}: {e}")
            return None

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
        # self._files_cache: Dict[int, list[str]] = {}  # Placeholder for file cache
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
        Loads tracks from the uber_tracks view into the cache.
        Handles minor schema variations (column name differences) gracefully.
        Returns True if loaded, False otherwise.
        """

        def get_col(r: sqlite3.Row, names: list[str], default=None):
            for n in names:
                try:
                    return r[n]
                except (KeyError, IndexError):
                    continue
            return default

        query = "SELECT * FROM uber_tracks"
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        if not rows:
            cursor.close()
            return True

        # Load tracks into cache, keyed by track_id (int)
        cache = self._tracks_cache
        for row in rows:
            tid = get_col(row, ["track_id", "id"])
            if tid is None:
                # Skip rows without a track identifier
                continue

            track = Track(
                track_id=tid,
                catalog_number=get_col(row, ["catalog_number", "catalog_no", "catalog"], ""),
                label=get_col(row, ["label", "label_name"], ""),
                album_title=get_col(row, ["album_title", "title"], ""),
                disc_number=get_col(row, ["disc_number", "disc_no"], 0),
                track_artist=get_col(row, ["track_artist", "artist", "album_artist"], ""),
                track_title=get_col(row, ["track_title", "name"], ""),
                format=get_col(row, ["format", "media"], ""),
                track_number=get_col(row, ["track_number", "track_no"], 0),
                discogs_id=get_col(row, ["discogs_id"], 0),
                year=get_col(row, ["year", "date"], 0),
                country=get_col(row, ["country"], ""),
                discogs_url=get_col(row, ["discogs_url", "url"], ""),
                album_artist=get_col(row, ["album_artist", "album_artist_name", "artist"], ""),
                file_location=get_col(row, ["file_location", "path", "file_path"], ""),
                style=get_col(row, ["style"], ""),
                genre=get_col(row, ["genre"], ""),
                file_id=get_col(row, ["track_file_id", "file_id", "file_file_id"], None),
            )

            cache[tid] = track
            self._track_list.append(track)

            discogs_id = get_col(row, ["discogs_id"], None)
            if discogs_id is not None and discogs_id not in self._releases_cache:
                release = Release(
                    discogs_id=discogs_id,
                    date=track.year,
                    country=track.country,
                    title=track.album_title,
                    album_artist_name=track.album_artist,
                    catalog_number=track.catalog_number,
                    label_name=track.label,
                )
                self._releases_cache[discogs_id] = release

            label_name = track.label or ""
            if label_name and label_name not in self._labels_cache:
                self._labels_cache[label_name] = RecordLabel(name=label_name)

            if discogs_id is not None:
                self._label_to_releases.setdefault(label_name, set()).add(discogs_id)
                self._release_to_tracks.setdefault(discogs_id, set()).add(tid)

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
