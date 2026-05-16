"""
tests/test_config_manager.py — unit tests for ConfigurationManager singleton.

Uses tmp_path + monkeypatch to:
- Redirect get_absolute_path_config to a temp file path
- Reset ConfigurationManager._instance to None before each test so the
  singleton does not bleed between tests
"""

import configparser
import os
import pytest

import config_manager as cm_module
from config_manager import ConfigurationManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_singleton():
    """Ensure singleton state is torn down before and after every test."""
    ConfigurationManager._instance = None
    yield
    ConfigurationManager._instance = None


@pytest.fixture()
def config_path(tmp_path, monkeypatch):
    """Point get_absolute_path_config at a temp path and return it."""
    cfg_file = tmp_path / "config.ini"
    monkeypatch.setattr(cm_module, "get_absolute_path_config", lambda: str(cfg_file))
    return cfg_file


@pytest.fixture()
def populated_config(config_path):
    """Write a minimal config.ini so properties return non-default values."""
    cfg = configparser.ConfigParser()
    cfg["Directories"] = {
        "last_source_directory": "/src/music",
        "last_target_directory": "/tgt/music",
        "last_left_directory": "/left",
        "last_right_directory": "/right",
    }
    cfg["Window"] = {"width": "1920", "height": "1080"}
    cfg["main_logger"] = {
        "log_dir": "/var/log/music",
        "clear_log_each_run": "true",
        "max_log_size": "5MB",
        "backup_count": "3",
    }
    cfg["discogs"] = {"token": "my-secret-token"}
    cfg["autotag"] = {"filename_mask": "{artist} - {title}"}
    cfg["db"] = {"location": "/data/db", "name": "music.db"}
    with open(config_path, "w") as fh:
        cfg.write(fh)
    return config_path


# ---------------------------------------------------------------------------
# T6-1: Singleton behaviour
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_two_calls_return_same_instance(self, config_path):
        a = ConfigurationManager()
        b = ConfigurationManager()
        assert a is b

    def test_reset_yields_new_instance(self, config_path):
        a = ConfigurationManager()
        ConfigurationManager._instance = None
        b = ConfigurationManager()
        # They won't be the same object since we reset between calls
        assert a is not b


# ---------------------------------------------------------------------------
# T6-2: Fallback values when config.ini does not exist
# ---------------------------------------------------------------------------

class TestFallbackValues:
    def test_last_source_directory_fallback(self, config_path):
        mgr = ConfigurationManager()
        assert mgr.last_source_directory == ""

    def test_last_target_directory_fallback(self, config_path):
        mgr = ConfigurationManager()
        assert mgr.last_target_directory == ""

    def test_last_left_directory_fallback(self, config_path):
        mgr = ConfigurationManager()
        assert mgr.last_left_directory == ""

    def test_last_right_directory_fallback(self, config_path):
        mgr = ConfigurationManager()
        assert mgr.last_right_directory == ""

    def test_window_width_fallback(self, config_path):
        mgr = ConfigurationManager()
        assert mgr.window_width == 1200

    def test_window_height_fallback(self, config_path):
        mgr = ConfigurationManager()
        assert mgr.window_height == 800

    def test_log_dir_fallback(self, config_path):
        mgr = ConfigurationManager()
        assert mgr.log_dir == "logs"

    def test_clear_log_each_run_fallback(self, config_path):
        mgr = ConfigurationManager()
        assert mgr.clear_log_each_run is False

    def test_max_log_size_fallback(self, config_path):
        mgr = ConfigurationManager()
        assert mgr.max_log_size == "10MB"

    def test_backup_count_fallback(self, config_path):
        mgr = ConfigurationManager()
        assert mgr.backup_count == 5

    def test_discogs_token_fallback(self, config_path):
        mgr = ConfigurationManager()
        assert mgr.discogs_token == ""

    def test_filename_mask_fallback(self, config_path):
        mgr = ConfigurationManager()
        assert mgr.filename_mask == ""

    def test_db_location_fallback(self, config_path):
        mgr = ConfigurationManager()
        assert mgr.db_location == ""

    def test_db_name_fallback(self, config_path):
        mgr = ConfigurationManager()
        assert mgr.db_name == "music_catalogue.db"


# ---------------------------------------------------------------------------
# T6-3: set() + get() roundtrip
# ---------------------------------------------------------------------------

class TestSetGet:
    def test_set_and_get_existing_section(self, config_path):
        mgr = ConfigurationManager()
        mgr.set("MySection", "mykey", "myvalue")
        assert mgr.get("MySection", "mykey") == "myvalue"

    def test_set_creates_missing_section(self, config_path):
        mgr = ConfigurationManager()
        mgr.set("NewSection", "newkey", "newval")
        assert mgr.get("NewSection", "newkey") == "newval"

    def test_set_overwrites_existing_value(self, config_path):
        mgr = ConfigurationManager()
        mgr.set("S", "k", "first")
        mgr.set("S", "k", "second")
        assert mgr.get("S", "k") == "second"

    def test_get_missing_key_returns_fallback(self, config_path):
        mgr = ConfigurationManager()
        assert mgr.get("NoSuchSection", "no_key", fallback="default") == "default"

    def test_get_missing_key_returns_empty_string_default(self, config_path):
        mgr = ConfigurationManager()
        assert mgr.get("NoSuchSection", "no_key") == ""


# ---------------------------------------------------------------------------
# T6-4: save() writes to the path returned by get_absolute_path_config()
# ---------------------------------------------------------------------------

class TestSave:
    def test_save_creates_file(self, config_path):
        mgr = ConfigurationManager()
        mgr.set("Test", "key", "val")
        mgr.save()
        assert config_path.exists()

    def test_save_persists_values(self, config_path):
        mgr = ConfigurationManager()
        mgr.set("Persist", "answer", "42")
        mgr.save()

        raw = configparser.ConfigParser()
        raw.read(str(config_path))
        assert raw.get("Persist", "answer") == "42"

    def test_save_round_trip_all_sections(self, config_path):
        mgr = ConfigurationManager()
        mgr.set("A", "x", "1")
        mgr.set("B", "y", "2")
        mgr.save()

        raw = configparser.ConfigParser()
        raw.read(str(config_path))
        assert raw["A"]["x"] == "1"
        assert raw["B"]["y"] == "2"


# ---------------------------------------------------------------------------
# T6-5: reload() re-reads from disk
# ---------------------------------------------------------------------------

class TestReload:
    def test_reload_picks_up_external_changes(self, config_path):
        mgr = ConfigurationManager()
        # Write a value not in memory via raw configparser
        raw = configparser.ConfigParser()
        raw["External"] = {"key": "from_disk"}
        with open(config_path, "w") as fh:
            raw.write(fh)

        mgr.reload()
        assert mgr.get("External", "key") == "from_disk"

    def test_reload_forgets_in_memory_only_values(self, config_path):
        mgr = ConfigurationManager()
        mgr.set("Volatile", "temp", "yes")
        # Do NOT save — just reload from (empty) disk
        mgr.reload()
        assert mgr.get("Volatile", "temp") == ""

    def test_reload_updates_properties(self, config_path):
        mgr = ConfigurationManager()
        assert mgr.log_dir == "logs"  # default

        raw = configparser.ConfigParser()
        raw["main_logger"] = {"log_dir": "/custom/logs"}
        with open(config_path, "w") as fh:
            raw.write(fh)

        mgr.reload()
        assert mgr.log_dir == "/custom/logs"


# ---------------------------------------------------------------------------
# T6-6: db_path combines db_location and db_name
# ---------------------------------------------------------------------------

class TestDbPath:
    def test_db_path_combines_location_and_name(self, populated_config):
        mgr = ConfigurationManager()
        expected = os.path.join("/data/db", "music.db")
        assert mgr.db_path == expected

    def test_db_path_with_set_values(self, config_path):
        mgr = ConfigurationManager()
        mgr.set("db", "location", "/my/location")
        mgr.set("db", "name", "catalogue.db")
        expected = os.path.join("/my/location", "catalogue.db")
        assert mgr.db_path == expected


# ---------------------------------------------------------------------------
# T6-7: db_path returns "" when either component is empty
# ---------------------------------------------------------------------------

class TestDbPathEmpty:
    def test_db_path_empty_when_no_config(self, config_path):
        # Both location (default "") and name has a default value —
        # only location being empty is enough to make path return ""
        mgr = ConfigurationManager()
        assert mgr.db_path == ""

    def test_db_path_empty_when_location_missing(self, config_path):
        mgr = ConfigurationManager()
        mgr.set("db", "name", "music.db")
        # location still ""
        assert mgr.db_path == ""

    def test_db_path_empty_when_name_missing(self, config_path):
        mgr = ConfigurationManager()
        mgr.set("db", "location", "/some/path")
        mgr.set("db", "name", "")
        assert mgr.db_path == ""

    def test_db_path_empty_when_both_missing(self, config_path):
        mgr = ConfigurationManager()
        mgr.set("db", "location", "")
        mgr.set("db", "name", "")
        assert mgr.db_path == ""
