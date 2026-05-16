import sqlite3
from dataclasses import dataclass
from typing import Dict, Optional

from log_config import get_logger

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
    id: int = 0        # same value as discogs_id; present for UI compatibility
    label_id: int = 0  # synthetic integer matching RecordLabel.id

    def __str__(self) -> str:
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
    id: int = 0  # synthetic integer assigned during load


class MusicCatalogDB:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._tracks_cache: Dict[int, Track] = {}
        self._releases_cache: Dict[int, Release] = {}
        # Labels indexed two ways: by synthetic int ID and by name.
        self._labels_by_id: Dict[int, RecordLabel] = {}
        self._labels_by_name: Dict[str, RecordLabel] = {}
        self._label_to_releases: Dict[str, set] = {}
        self._release_to_tracks: Dict[int, set] = {}
        self._track_list: list[Track] = []
        self._next_label_id: int = 1
        self.connection: Optional[sqlite3.Connection] = None

    def get_waveform_data(self, file_id: int) -> Optional[bytes]:
        """Fetch waveform_data BLOB for a given file_id from track_meta_data."""
        conn = self.__connect()
        if conn is None:
            return None
        try:
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
        finally:
            conn.close()

    def __connect(self) -> Optional[sqlite3.Connection]:
        try:
            connection = sqlite3.connect(self.db_path)
            logger.info("Connected to SQLite database.")
            return connection
        except sqlite3.Error as e:
            logger.info(f"Error connecting to database: {e}")
        return None

    def load(self) -> bool:
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
            logger.error(f"Failed to load tracks and releases: {e}")
            return False
        finally:
            connection.close()

    def __load_tracks(self, conn: sqlite3.Connection) -> bool:
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

        for row in rows:
            tid = get_col(row, ["track_id", "id"])
            if tid is None:
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

            self._tracks_cache[tid] = track
            self._track_list.append(track)

            # Assign a synthetic integer ID to each unique label name.
            label_name = track.label or ""
            if label_name and label_name not in self._labels_by_name:
                label_obj = RecordLabel(name=label_name, id=self._next_label_id)
                self._labels_by_name[label_name] = label_obj
                self._labels_by_id[self._next_label_id] = label_obj
                self._next_label_id += 1

            label_obj = self._labels_by_name.get(label_name)
            label_id_val = label_obj.id if label_obj else 0

            discogs_id = get_col(row, ["discogs_id"], None)
            if discogs_id is not None and discogs_id not in self._releases_cache:
                release = Release(
                    discogs_id=discogs_id,
                    id=discogs_id,
                    label_id=label_id_val,
                    date=str(track.year),
                    country=track.country,
                    title=track.album_title,
                    album_artist_name=track.album_artist,
                    catalog_number=track.catalog_number,
                    label_name=label_name,
                )
                self._releases_cache[discogs_id] = release

            if discogs_id is not None:
                self._label_to_releases.setdefault(label_name, set()).add(discogs_id)
                self._release_to_tracks.setdefault(discogs_id, set()).add(tid)

        cursor.close()
        return True

    # ── Dict-returning accessors (for UI compatibility) ────────────────────

    def get_labels(self) -> Dict[int, RecordLabel]:
        return self._labels_by_id

    def get_releases(self) -> Dict[int, Release]:
        return self._releases_cache

    def get_tracks(self) -> Dict[int, Track]:
        return self._tracks_cache

    # ── List-returning accessors ───────────────────────────────────────────

    def get_all_tracks(self) -> list[Track]:
        return self._track_list

    def get_all_labels(self) -> list[RecordLabel]:
        return list(self._labels_by_id.values())

    def get_tracks_for_label(self, label_name: str) -> list[Track]:
        track_ids = set()
        for release_id in self._label_to_releases.get(label_name, set()):
            track_ids.update(self._release_to_tracks.get(release_id, set()))
        return [self._tracks_cache[tid] for tid in track_ids]

    def get_releases_for_label(self, label_name: str) -> list[Release]:
        return [self._releases_cache[rid] for rid in self._label_to_releases.get(label_name, set())]

    def get_labels_and_releases(self) -> Dict[str, set]:
        return self._label_to_releases

    def get_release_by_id(self, release_id: int) -> Optional[Release]:
        return self._releases_cache.get(release_id)

    def count_tracks(self) -> int:
        return len(self._tracks_cache)

    def count_releases(self) -> int:
        return len(self._releases_cache)

    def close(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("SQLite connection closed.")


if __name__ == "__main__":
    db = MusicCatalogDB("music_catalog.db")
    ok = db.load()
    print("Loaded tracks:", len(db.get_all_tracks()) if ok else 0)
    db.close()
