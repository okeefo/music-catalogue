"""
Tests for src/file_operations/repackage_dir.py

Functions under test:
  - repackage_dir_by_label(source_dir, target_dir)
  - repackage_files_by_label(files, source_dir, target_dir)
  - repackage_file_by_label(file, source_dir, target_dir, user_choice)

Strategy:
  - conftest.py stubs out PyQt5, log_config, path_helper, taglib, and mutagen
    before any test module is imported, so the src/ modules can be loaded
    without the full application environment.
  - The module-level `audio_tags` instance inside repackage_dir is replaced
    with a MagicMock via the _patch_audio_tags_instance fixture.
  - shutil.move is patched per-test so no real filesystem moves occur.
  - tmp_path (pytest built-in) is used wherever real files/dirs are needed.
  - QMessageBox integer constants are defined here (matching Qt5 values) so
    the tests do not depend on PyQt5 being importable.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

# QMessageBox button result constants (standard Qt5 integer values).
# These must match the constants set in conftest.py for the mock to behave
# identically to the real Qt library.
_YES        = 16384
_NO         = 65536
_YES_TO_ALL = 32768
_NO_TO_ALL  = 131072
_CANCEL     = 4194304


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_audio_tags_mock(is_supported=True, tags=None):
    """Return a MagicMock replacing an AudioTagHelper instance."""
    m = MagicMock()
    m.isSupportedAudioFile.return_value = is_supported
    m.get_tags.return_value = tags if tags is not None else {"LABEL": ["Test Label"]}
    return m


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _patch_audio_tags_instance(monkeypatch):
    """
    Replace the module-level `audio_tags` object in repackage_dir with a
    fresh MagicMock before every test so tests are independent.
    Returns the mock so individual tests can adjust its behaviour.
    """
    import file_operations.repackage_dir as rd
    mock = _make_audio_tags_mock()
    monkeypatch.setattr(rd, "audio_tags", mock)
    return mock


# ---------------------------------------------------------------------------
# repackage_file_by_label — core logic
# ---------------------------------------------------------------------------

class TestRepackageFileByLabel:

    def test_skips_directory(self, tmp_path):
        """A path that resolves to a directory on disk is skipped immediately."""
        import file_operations.repackage_dir as rd

        subdir = tmp_path / "subdir"
        subdir.mkdir()

        result = rd.repackage_file_by_label(subdir.name, str(tmp_path), str(tmp_path), user_choice=0)

        assert result == 0
        rd.audio_tags.isSupportedAudioFile.assert_not_called()

    def test_skips_unsupported_file(self, tmp_path):
        """A file not recognised as a supported audio format is skipped."""
        import file_operations.repackage_dir as rd

        fake_file = tmp_path / "image.jpg"
        fake_file.write_bytes(b"")
        rd.audio_tags.isSupportedAudioFile.return_value = False

        result = rd.repackage_file_by_label(fake_file.name, str(tmp_path), str(tmp_path), user_choice=0)

        assert result == 0
        rd.audio_tags.get_tags.assert_not_called()

    def test_skips_file_with_no_tags(self, tmp_path):
        """A supported audio file that returns an empty tag dict is skipped."""
        import file_operations.repackage_dir as rd

        fake_mp3 = tmp_path / "track.mp3"
        fake_mp3.write_bytes(b"")
        rd.audio_tags.isSupportedAudioFile.return_value = True
        rd.audio_tags.get_tags.return_value = {}

        result = rd.repackage_file_by_label(fake_mp3.name, str(tmp_path), str(tmp_path), user_choice=0)

        assert result == 0

    def test_moves_file_when_target_does_not_exist(self, tmp_path):
        """
        When the target file does not already exist the source is moved via
        shutil.move into <target_dir>/<label>/<filename>.
        """
        import file_operations.repackage_dir as rd

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        fake_mp3 = source_dir / "track.mp3"
        fake_mp3.write_bytes(b"ID3")

        rd.audio_tags.isSupportedAudioFile.return_value = True
        rd.audio_tags.get_tags.return_value = {"LABEL": ["Cool Label"]}

        with patch("file_operations.repackage_dir.shutil.move") as mock_move:
            result = rd.repackage_file_by_label(
                fake_mp3.name, str(source_dir), str(target_dir), user_choice=0
            )

        expected_target = os.path.join(str(target_dir), "Cool Label", fake_mp3.name)
        mock_move.assert_called_once_with(str(fake_mp3), expected_target)
        # user_choice is unchanged when no dialog is required
        assert result == 0

    def test_uses_unknown_publisher_when_no_label_tag(self, tmp_path):
        """
        When tags exist but there is no LABEL key the file is placed under
        'Unknown Publisher'.
        """
        import file_operations.repackage_dir as rd

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        fake_mp3 = source_dir / "track.mp3"
        fake_mp3.write_bytes(b"ID3")

        rd.audio_tags.isSupportedAudioFile.return_value = True
        rd.audio_tags.get_tags.return_value = {"TITLE": ["My Track"]}  # no LABEL key

        with patch("file_operations.repackage_dir.shutil.move") as mock_move:
            rd.repackage_file_by_label(
                fake_mp3.name, str(source_dir), str(target_dir), user_choice=0
            )

        expected_target = os.path.join(str(target_dir), "Unknown Publisher", fake_mp3.name)
        mock_move.assert_called_once_with(str(fake_mp3), expected_target)

    def test_skips_existing_file_when_no_to_all(self, tmp_path):
        """
        With NoToAll as the prior user_choice, an already-existing target file
        must not be overwritten and no dialog must be shown.
        """
        import file_operations.repackage_dir as rd

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        target_dir = tmp_path / "target"
        label_dir = target_dir / "My Label"
        label_dir.mkdir(parents=True)

        fake_mp3 = source_dir / "track.mp3"
        fake_mp3.write_bytes(b"ID3")
        (label_dir / "track.mp3").write_bytes(b"existing")  # target already exists

        rd.audio_tags.isSupportedAudioFile.return_value = True
        rd.audio_tags.get_tags.return_value = {"LABEL": ["My Label"]}

        with patch("file_operations.repackage_dir.shutil.move") as mock_move:
            result = rd.repackage_file_by_label(
                fake_mp3.name, str(source_dir), str(target_dir),
                user_choice=_NO_TO_ALL
            )

        mock_move.assert_not_called()
        assert result == _NO_TO_ALL

    def test_overwrites_existing_file_when_yes_to_all(self, tmp_path):
        """
        With YesToAll as the prior user_choice, an already-existing target
        file is overwritten without showing a dialog.
        """
        import file_operations.repackage_dir as rd

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        target_dir = tmp_path / "target"
        label_dir = target_dir / "My Label"
        label_dir.mkdir(parents=True)

        fake_mp3 = source_dir / "track.mp3"
        fake_mp3.write_bytes(b"ID3")
        (label_dir / "track.mp3").write_bytes(b"existing")

        rd.audio_tags.isSupportedAudioFile.return_value = True
        rd.audio_tags.get_tags.return_value = {"LABEL": ["My Label"]}

        with patch("file_operations.repackage_dir.shutil.move") as mock_move:
            result = rd.repackage_file_by_label(
                fake_mp3.name, str(source_dir), str(target_dir),
                user_choice=_YES_TO_ALL
            )

        expected_target = os.path.join(str(label_dir), fake_mp3.name)
        mock_move.assert_called_once_with(str(fake_mp3), expected_target)
        assert result == _YES_TO_ALL


# ---------------------------------------------------------------------------
# repackage_files_by_label — batch logic
# ---------------------------------------------------------------------------

class TestRepackageFilesByLabel:

    def test_processes_multiple_files(self, tmp_path):
        """All files supplied in the list are individually processed."""
        import file_operations.repackage_dir as rd

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        for name in ("a.mp3", "b.mp3", "c.mp3"):
            (source_dir / name).write_bytes(b"ID3")

        rd.audio_tags.isSupportedAudioFile.return_value = True
        rd.audio_tags.get_tags.return_value = {"LABEL": ["Label X"]}

        with patch("file_operations.repackage_dir.shutil.move") as mock_move:
            rd.repackage_files_by_label(
                ["a.mp3", "b.mp3", "c.mp3"], str(source_dir), str(target_dir)
            )

        assert mock_move.call_count == 3

    def test_skips_subdirectories_in_file_list(self, tmp_path):
        """Entries in the file list that resolve to directories are skipped."""
        import file_operations.repackage_dir as rd

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "subdir").mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        rd.audio_tags.isSupportedAudioFile.return_value = True
        rd.audio_tags.get_tags.return_value = {"LABEL": ["Label Y"]}

        with patch("file_operations.repackage_dir.shutil.move") as mock_move:
            rd.repackage_files_by_label(["subdir"], str(source_dir), str(target_dir))

        mock_move.assert_not_called()

    def test_stops_processing_after_cancel(self, tmp_path):
        """
        When repackage_file_by_label returns Cancel for the first file the
        loop must terminate and the second file must not be processed.
        """
        import file_operations.repackage_dir as rd

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        for name in ("a.mp3", "b.mp3"):
            (source_dir / name).write_bytes(b"ID3")

        with patch.object(rd, "repackage_file_by_label", return_value=_CANCEL) as mock_rfbl:
            rd.repackage_files_by_label(["a.mp3", "b.mp3"], str(source_dir), str(target_dir))

        assert mock_rfbl.call_count == 1


# ---------------------------------------------------------------------------
# repackage_dir_by_label — directory-level entry point
# ---------------------------------------------------------------------------

class TestRepackageDirByLabel:

    def test_delegates_to_repackage_files_with_full_listing(self, tmp_path):
        """
        repackage_dir_by_label must call repackage_files_by_label with the
        os.listdir result and the correct source/target paths.
        """
        import file_operations.repackage_dir as rd

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        (source_dir / "track1.mp3").write_bytes(b"ID3")
        (source_dir / "track2.mp3").write_bytes(b"ID3")

        with patch.object(rd, "repackage_files_by_label") as mock_rfbl:
            rd.repackage_dir_by_label(str(source_dir), str(target_dir))

        mock_rfbl.assert_called_once()
        args = mock_rfbl.call_args[0]
        # First arg is the file list from os.listdir — order not guaranteed
        assert set(args[0]) == {"track1.mp3", "track2.mp3"}
        assert args[1] == str(source_dir)
        assert args[2] == str(target_dir)

    def test_empty_directory_calls_repackage_files_with_empty_list(self, tmp_path):
        """An empty source directory results in an empty file list being passed."""
        import file_operations.repackage_dir as rd

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        with patch.object(rd, "repackage_files_by_label") as mock_rfbl:
            rd.repackage_dir_by_label(str(source_dir), str(target_dir))

        mock_rfbl.assert_called_once()
        args = mock_rfbl.call_args[0]
        assert args[0] == []
        assert args[1] == str(source_dir)
        assert args[2] == str(target_dir)
