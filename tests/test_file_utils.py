"""
Tests for src/file_operations/file_utils.py

Functions under test:
  - ask_and_copy_files(file_list, target_dir)
  - ask_and_move_files(file_list, source_dir, target_dir)
  - __normalise_paths (exercised indirectly via ask_and_move_files)

Strategy:
  - conftest.py stubs out PyQt5, log_config, path_helper, taglib, and mutagen.
  - ui.progress_bar_helper is stubbed here (before file_utils is imported) so
    that the from-import in file_utils does not raise ModuleNotFoundError.
  - show_message_box is patched at the file_utils module level
    ("file_operations.file_utils.show_message_box") — this is the correct
    target because file_utils has already bound the name into its own namespace
    via `from ui.custom_messagebox import … show_message_box`.
  - shutil.move and shutil.copy2 are patched to avoid real filesystem ops.
  - send2trash is stubbed at the module level so we never interact with the
    OS recycle bin.
  - tmp_path (pytest built-in) is used for any real path references.

QMessageBox integer constants used here match the values in conftest.py.
"""

import os
import sys
import types
import pytest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# QMessageBox button constants (must match conftest.py / standard Qt5 values)
# ---------------------------------------------------------------------------
_YES        = 16384
_NO         = 65536
_YES_TO_ALL = 32768
_NO_TO_ALL  = 131072
_CANCEL     = 4194304

# Patch target: show_message_box as bound in the file_utils namespace
_SHOW_MB = "file_operations.file_utils.show_message_box"

# ---------------------------------------------------------------------------
# Module-level stub for send2trash (avoids touching the OS recycle bin).
# Must be registered before file_utils is imported.
# ---------------------------------------------------------------------------
_send2trash_stub = types.ModuleType("send2trash")
_send2trash_stub.send2trash = MagicMock()
sys.modules.setdefault("send2trash", _send2trash_stub)


# ---------------------------------------------------------------------------
# Module-level stub for ui.progress_bar_helper.
# conftest.py creates a bare `ui` module stub (not a real package), so
# ui.progress_bar_helper cannot be imported the normal way.  We register it
# directly in sys.modules before file_utils is imported so the
# `from ui.progress_bar_helper import ProgressBarHelper` line in file_utils
# succeeds.
# ---------------------------------------------------------------------------
_pb_helper_stub = types.ModuleType("ui.progress_bar_helper")
_ProgressBarHelper_mock = MagicMock()
_pb_instance_mock = MagicMock()
_pb_instance_mock.user_has_cancelled.return_value = False
_ProgressBarHelper_mock.return_value = _pb_instance_mock
_pb_helper_stub.ProgressBarHelper = _ProgressBarHelper_mock
sys.modules.setdefault("ui.progress_bar_helper", _pb_helper_stub)


# ---------------------------------------------------------------------------
# Import the module under test (after all stubs are in place).
# ---------------------------------------------------------------------------
import file_operations.file_utils as _fu_module   # noqa: E402  (intentional late import)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def fu():
    """Return the file_utils module."""
    return _fu_module


# ---------------------------------------------------------------------------
# ask_and_copy_files — empty list
# ---------------------------------------------------------------------------

class TestAskAndCopyFilesEmptyList:

    def test_does_nothing_when_file_list_is_empty(self, fu):
        """ask_and_copy_files must return immediately when file_list is []."""
        with patch(_SHOW_MB) as mock_mb, \
             patch("shutil.copy2") as mock_copy:

            fu.ask_and_copy_files([], target_dir="/some/target")

            mock_mb.assert_not_called()
            mock_copy.assert_not_called()

    def test_does_nothing_when_file_list_is_none(self, fu):
        """ask_and_copy_files treats None as a falsy empty list."""
        with patch(_SHOW_MB) as mock_mb, \
             patch("shutil.copy2") as mock_copy:

            fu.ask_and_copy_files(None, target_dir="/some/target")

            mock_mb.assert_not_called()
            mock_copy.assert_not_called()


# ---------------------------------------------------------------------------
# ask_and_move_files — empty list
# ---------------------------------------------------------------------------

class TestAskAndMoveFilesEmptyList:

    def test_does_nothing_when_file_list_is_empty(self, fu):
        """ask_and_move_files must return immediately when file_list is []."""
        with patch(_SHOW_MB) as mock_mb, \
             patch("shutil.move") as mock_move:

            fu.ask_and_move_files([], source_dir="/src", target_dir="/dst")

            mock_mb.assert_not_called()
            mock_move.assert_not_called()


# ---------------------------------------------------------------------------
# __normalise_paths — exercised via ask_and_move_files
# ---------------------------------------------------------------------------

class TestNormalisePaths:

    def test_source_and_target_dirs_are_normalised(self, fu, tmp_path):
        """
        Paths with redundant separators are normalised before the dialog is
        shown.  We verify normalisation by inspecting the message text passed
        to show_message_box — it must contain the normalised target path.
        """
        raw_source = str(tmp_path) + os.sep + os.sep + "src"
        raw_target = str(tmp_path) + os.sep + os.sep + "dst"

        expected_target = os.path.normpath(raw_target)

        with patch(_SHOW_MB, return_value=_CANCEL) as mock_mb:
            fu.ask_and_move_files(["file.mp3"], source_dir=raw_source, target_dir=raw_target)

        # The normalised target path must appear in the dialog message
        call_args = mock_mb.call_args
        assert call_args is not None
        message_text = call_args[0][0]   # first positional arg is the message
        assert expected_target in message_text

    def test_file_paths_in_list_are_normalised(self, fu, tmp_path):
        """
        File names in the list are joined with source_dir and normalised
        before the move dialog is shown.
        """
        source_dir = str(tmp_path / "source")
        target_dir = str(tmp_path / "target")

        # A relative file name with a redundant dot-segment
        file_name = "subdir/../track.mp3"
        normalised_name = os.path.basename(os.path.normpath(os.path.join(source_dir, file_name)))

        with patch(_SHOW_MB, return_value=_CANCEL) as mock_mb:
            fu.ask_and_move_files([file_name], source_dir=source_dir, target_dir=target_dir)

        call_args = mock_mb.call_args
        assert call_args is not None
        message_text = call_args[0][0]
        assert normalised_name in message_text


# ---------------------------------------------------------------------------
# ask_and_copy_files — Cancel skips the copy operation
# ---------------------------------------------------------------------------

class TestAskAndCopyFilesCancel:

    def test_no_copy_when_user_cancels(self, fu, tmp_path):
        """When show_message_box returns Cancel no file should be copied."""
        file_list = ["track1.mp3", "track2.mp3"]
        target_dir = str(tmp_path / "target")

        with patch(_SHOW_MB, return_value=_CANCEL), \
             patch("shutil.copy2") as mock_copy, \
             patch("shutil.copytree") as mock_copytree:

            fu.ask_and_copy_files(file_list, target_dir=target_dir)

            mock_copy.assert_not_called()
            mock_copytree.assert_not_called()

    def test_no_copy_when_user_says_no(self, fu, tmp_path):
        """When show_message_box returns No (non-Yes) no file should be copied."""
        file_list = ["track1.mp3"]
        target_dir = str(tmp_path / "target")

        with patch(_SHOW_MB, return_value=_NO), \
             patch("shutil.copy2") as mock_copy:

            fu.ask_and_copy_files(file_list, target_dir=target_dir)

            mock_copy.assert_not_called()


# ---------------------------------------------------------------------------
# ask_and_move_files — Cancel skips the move operation
# ---------------------------------------------------------------------------

class TestAskAndMoveFilesCancel:

    def test_no_move_when_user_cancels(self, fu, tmp_path):
        """When show_message_box returns Cancel no file should be moved."""
        source_dir = str(tmp_path / "source")
        target_dir = str(tmp_path / "target")
        file_list = ["track.wav"]

        with patch(_SHOW_MB, return_value=_CANCEL), \
             patch("shutil.move") as mock_move:

            fu.ask_and_move_files(file_list, source_dir=source_dir, target_dir=target_dir)

            mock_move.assert_not_called()

    def test_no_move_when_user_says_no(self, fu, tmp_path):
        """When show_message_box returns No no file should be moved."""
        source_dir = str(tmp_path / "source")
        target_dir = str(tmp_path / "target")
        file_list = ["track.wav"]

        with patch(_SHOW_MB, return_value=_NO), \
             patch("shutil.move") as mock_move:

            fu.ask_and_move_files(file_list, source_dir=source_dir, target_dir=target_dir)

            mock_move.assert_not_called()


# ---------------------------------------------------------------------------
# ask_and_move_files — Yes proceeds with the move
# ---------------------------------------------------------------------------

class TestAskAndMoveFilesYes:

    def test_move_called_when_user_confirms(self, fu, tmp_path):
        """When the user selects Yes the file is moved via shutil.move."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Create a real file so os.path.exists checks pass
        track = source_dir / "track.wav"
        track.write_bytes(b"RIFF")

        with patch(_SHOW_MB, return_value=_YES), \
             patch("shutil.move") as mock_move:

            fu.ask_and_move_files(
                ["track.wav"],
                source_dir=str(source_dir),
                target_dir=str(target_dir),
            )

        mock_move.assert_called_once_with(str(track), str(target_dir))


# ---------------------------------------------------------------------------
# ask_and_copy_files — Yes proceeds with the copy
# ---------------------------------------------------------------------------

class TestAskAndCopyFilesYes:

    def test_copy_called_for_each_file_when_user_confirms(self, fu, tmp_path):
        """When the user selects Yes each file is copied via shutil.copy2."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        files = []
        for name in ("a.wav", "b.wav"):
            f = source_dir / name
            f.write_bytes(b"RIFF")
            files.append(str(f))

        # os.path.exists for target files returns False (no conflict)
        with patch(_SHOW_MB, return_value=_YES), \
             patch("os.path.exists", return_value=False), \
             patch("os.path.isfile", return_value=True), \
             patch("shutil.copy2") as mock_copy:

            fu.ask_and_copy_files(files, target_dir=str(target_dir))

        assert mock_copy.call_count == 2
