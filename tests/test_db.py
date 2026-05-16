"""
Tests for src/db/db_reader.py (MusicCatalogDB_2) and src/db/db_manager.py (setup_database).

Strategy:
  - conftest.py stubs out PyQt5, log_config, path_helper, taglib, and mutagen
    before any test module is imported.
  - setup_database() reads config via ConfigurationManager (a singleton); we
    patch ConfigurationManager at the module level in db_manager so the
    function uses a controlled, tmp_path-based DB path without touching disk
    or config.ini.
  - MusicCatalogDB_2 is tested directly against real in-memory / tmp SQLite
    databases so the SQL logic is exercised without mocking sqlite3.
"""

import os
import sqlite3
import pytest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# T4-1: setup_database() creates the expected tables in a fresh SQLite DB
# ---------------------------------------------------------------------------

class TestSetupDatabase:
    """setup_database() must create the expected schema objects."""

    def _get_table_names(self, db_path: str):
        """Return set of table names present in the SQLite file."""
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        return {r[0] for r in rows}

    def test_creates_expected_tables(self, tmp_path):
        """setup_database creates release, tracks, media_types, _vinyl_copies, digital_media."""
        db_file = tmp_path / "test_catalog.db"

        # Patch ConfigurationManager so setup_database uses our tmp_path DB.
        cfg_mock = MagicMock()
        cfg_mock.db_location = str(tmp_path)
        cfg_mock.get.side_effect = lambda section, key, **kw: (
            "test_catalog.db" if (section, key) == ("db", "name") else kw.get("fallback", "")
        )
        cfg_mock.db_path = str(db_file)

        # ConfigurationManager is a singleton; patch where db_manager imports it.
        with patch("db.db_manager.ConfigurationManager", return_value=cfg_mock):
            from db.db_manager import setup_database
            setup_database()

        tables = self._get_table_names(str(db_file))
        assert "release" in tables
        assert "tracks" in tables
        assert "media_types" in tables
        assert "_vinyl_copies" in tables
        assert "digital_media" in tables

    def test_media_types_seeded(self, tmp_path):
        """setup_database inserts WAV, MP3, and VINYL into media_types."""
        db_file = tmp_path / "seed_test.db"

        cfg_mock = MagicMock()
        cfg_mock.db_location = str(tmp_path)
        cfg_mock.get.side_effect = lambda section, key, **kw: (
            "seed_test.db" if (section, key) == ("db", "name") else kw.get("fallback", "")
        )
        cfg_mock.db_path = str(db_file)

        with patch("db.db_manager.ConfigurationManager", return_value=cfg_mock):
            from db import db_manager
            # Reset module-level cached import so patch takes effect
            db_manager.setup_database()

        with sqlite3.connect(str(db_file)) as conn:
            formats = {r[0] for r in conn.execute("SELECT format FROM media_types").fetchall()}

        assert "WAV" in formats
        assert "MP3" in formats
        assert "VINYL" in formats


# ---------------------------------------------------------------------------
# T4-2: MusicCatalogDB_2 — constructor does NOT open a connection
# ---------------------------------------------------------------------------

class TestMusicCatalogDB2Init:

    def test_connection_is_none_after_init(self, tmp_path):
        """__init__ must not open a connection; self.connection stays None."""
        from db.db_reader import MusicCatalogDB_2

        db_path = str(tmp_path / "catalog.db")
        db = MusicCatalogDB_2(db_path)

        assert db.connection is None

    def test_caches_are_empty_after_init(self, tmp_path):
        """All internal caches start empty."""
        from db.db_reader import MusicCatalogDB_2

        db = MusicCatalogDB_2(str(tmp_path / "catalog.db"))

        assert db._tracks_cache == {}
        assert db._releases_cache == {}
        assert db._labels_cache == {}
        assert db._track_list == []


# ---------------------------------------------------------------------------
# T4-3: MusicCatalogDB_2.close() sets self.connection to None
# ---------------------------------------------------------------------------

class TestMusicCatalogDB2Close:

    def test_close_with_open_connection_sets_none(self, tmp_path):
        """close() must close an open connection and set self.connection to None."""
        from db.db_reader import MusicCatalogDB_2

        db_path = str(tmp_path / "catalog.db")
        db = MusicCatalogDB_2(db_path)

        # Manually assign a real connection to simulate an open state.
        db.connection = sqlite3.connect(db_path)
        assert db.connection is not None

        db.close()

        assert db.connection is None

    def test_close_when_already_none_is_safe(self, tmp_path):
        """close() on a freshly-created instance (connection=None) must not raise."""
        from db.db_reader import MusicCatalogDB_2

        db = MusicCatalogDB_2(str(tmp_path / "catalog.db"))
        # Should not raise even though connection is None
        db.close()
        assert db.connection is None


# ---------------------------------------------------------------------------
# T4-4: MusicCatalogDB_2.load() behaviour
# ---------------------------------------------------------------------------

class TestMusicCatalogDB2Load:

    def _make_db_with_uber_tracks(self, path: str) -> None:
        """Create a minimal SQLite DB that includes the uber_tracks view."""
        with sqlite3.connect(path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS uber_tracks (
                    track_id      INTEGER PRIMARY KEY,
                    catalog_number TEXT,
                    label_name    TEXT,
                    album_title   TEXT,
                    disc_number   INTEGER,
                    track_artist  TEXT,
                    track_title   TEXT,
                    format        TEXT,
                    track_number  INTEGER,
                    discogs_id    INTEGER,
                    year          TEXT,
                    country       TEXT,
                    discogs_url   TEXT,
                    album_artist  TEXT,
                    file_location TEXT,
                    style         TEXT,
                    genre         TEXT,
                    file_id       INTEGER
                )
            """)
            conn.commit()

    def test_load_returns_true_when_uber_tracks_view_exists_and_is_empty(self, tmp_path):
        """load() returns True when uber_tracks exists but contains no rows."""
        from db.db_reader import MusicCatalogDB_2

        db_path = str(tmp_path / "catalog.db")
        self._make_db_with_uber_tracks(db_path)

        db = MusicCatalogDB_2(db_path)
        result = db.load()

        assert result is True

    def test_load_returns_false_when_uber_tracks_view_is_missing(self, tmp_path):
        """load() returns False gracefully when the uber_tracks view/table is absent."""
        from db.db_reader import MusicCatalogDB_2

        db_path = str(tmp_path / "empty.db")
        # Create an empty SQLite database (no uber_tracks table/view)
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE unrelated (id INTEGER PRIMARY KEY)")
            conn.commit()

        db = MusicCatalogDB_2(db_path)
        result = db.load()

        assert result is False

    def test_load_populates_tracks_cache(self, tmp_path):
        """load() fills the internal cache with rows from uber_tracks."""
        from db.db_reader import MusicCatalogDB_2

        db_path = str(tmp_path / "catalog.db")
        self._make_db_with_uber_tracks(db_path)

        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                INSERT INTO uber_tracks
                    (track_id, catalog_number, label_name, album_title, disc_number,
                     track_artist, track_title, format, track_number, discogs_id,
                     year, country, discogs_url, album_artist, file_location,
                     style, genre, file_id)
                VALUES (1, 'CAT001', 'Test Label', 'Test Album', 1,
                        'Artist A', 'Track One', 'WAV', 1, 12345,
                        '2020', 'UK', 'https://discogs.com/1', 'Artist A',
                        '/music/track.wav', 'Electronic', 'Techno', 99)
            """)
            conn.commit()

        db = MusicCatalogDB_2(db_path)
        result = db.load()

        assert result is True
        assert db.count_tracks() == 1
        track = db._track_list[0]
        assert track.track_id == 1
        assert track.album_title == "Test Album"

    def test_load_does_not_set_self_connection(self, tmp_path):
        """load() opens its own internal connection and does not assign self.connection."""
        from db.db_reader import MusicCatalogDB_2

        db_path = str(tmp_path / "catalog.db")
        self._make_db_with_uber_tracks(db_path)

        db = MusicCatalogDB_2(db_path)
        db.load()

        # self.connection must remain None — load() manages its own connection
        assert db.connection is None


# ---------------------------------------------------------------------------
# T4-5: MusicCatalogDB_2.get_waveform_data() returns None when no data
# ---------------------------------------------------------------------------

class TestMusicCatalogDB2GetWaveformData:

    def _make_db_with_meta_table(self, path: str) -> None:
        """Create a DB that contains the track_meta_data table."""
        with sqlite3.connect(path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS track_meta_data (
                    id            INTEGER PRIMARY KEY,
                    waveform_data BLOB
                )
            """)
            conn.commit()

    def test_returns_none_when_file_id_not_found(self, tmp_path):
        """get_waveform_data returns None if no row matches the file_id."""
        from db.db_reader import MusicCatalogDB_2

        db_path = str(tmp_path / "waveform.db")
        self._make_db_with_meta_table(db_path)

        db = MusicCatalogDB_2(db_path)
        result = db.get_waveform_data(file_id=999)

        assert result is None

    def test_returns_none_when_waveform_data_is_null(self, tmp_path):
        """get_waveform_data returns None when the row exists but waveform_data is NULL."""
        from db.db_reader import MusicCatalogDB_2

        db_path = str(tmp_path / "waveform.db")
        self._make_db_with_meta_table(db_path)

        with sqlite3.connect(db_path) as conn:
            conn.execute("INSERT INTO track_meta_data (id, waveform_data) VALUES (1, NULL)")
            conn.commit()

        db = MusicCatalogDB_2(db_path)
        result = db.get_waveform_data(file_id=1)

        assert result is None

    def test_returns_blob_when_data_exists(self, tmp_path):
        """get_waveform_data returns the stored bytes when waveform_data is set."""
        from db.db_reader import MusicCatalogDB_2

        db_path = str(tmp_path / "waveform.db")
        self._make_db_with_meta_table(db_path)

        sample_data = b"\x00\x01\x02\x03\xff"
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO track_meta_data (id, waveform_data) VALUES (7, ?)",
                (sample_data,),
            )
            conn.commit()

        db = MusicCatalogDB_2(db_path)
        result = db.get_waveform_data(file_id=7)

        assert result == sample_data

    def test_returns_none_when_db_path_is_invalid(self, tmp_path):
        """get_waveform_data returns None gracefully when the DB file does not exist."""
        from db.db_reader import MusicCatalogDB_2

        db = MusicCatalogDB_2(str(tmp_path / "nonexistent" / "catalog.db"))
        # SQLite will create a new empty DB, then the table won't exist → should return None
        result = db.get_waveform_data(file_id=1)

        assert result is None
