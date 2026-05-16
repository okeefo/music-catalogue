"""
tests/test_audio_tags.py — unit tests for AudioTagHelper.

conftest.py already stubs taglib and all mutagen sub-modules at import time,
so we can patch them freely with MagicMock inside individual tests without
triggering native-extension errors.

isSupportedAudioFile uses pathlib.Path.is_file(), so tests that exercise the
"happy-path" of that method need a real file on disk (created via tmp_path).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from file_operations.audio_tags import AudioTagHelper, AUDIO_EXTENSIONS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_file(tmp_path: Path, name: str) -> Path:
    """Create an empty file with the given name and return its Path."""
    p = tmp_path / name
    p.touch()
    return p


# ---------------------------------------------------------------------------
# T3-1: isSupportedAudioFile — supported extensions
# ---------------------------------------------------------------------------

class TestIsSupportedAudioFile:
    def test_mp3_returns_true(self, tmp_path):
        helper = AudioTagHelper()
        f = _make_file(tmp_path, "track.mp3")
        assert helper.isSupportedAudioFile(str(f)) is True

    def test_wav_returns_true(self, tmp_path):
        helper = AudioTagHelper()
        f = _make_file(tmp_path, "track.wav")
        assert helper.isSupportedAudioFile(str(f)) is True

    def test_flac_returns_true(self, tmp_path):
        helper = AudioTagHelper()
        f = _make_file(tmp_path, "track.flac")
        assert helper.isSupportedAudioFile(str(f)) is True

    def test_all_supported_extensions_covered(self):
        """Sanity-check that AUDIO_EXTENSIONS matches what we test."""
        assert set(AUDIO_EXTENSIONS) == {".mp3", ".wav", ".flac"}

    # -----------------------------------------------------------------------
    # T3-2: isSupportedAudioFile — unsupported extensions
    # -----------------------------------------------------------------------

    def test_jpg_returns_false(self, tmp_path):
        helper = AudioTagHelper()
        f = _make_file(tmp_path, "cover.jpg")
        assert helper.isSupportedAudioFile(str(f)) is False

    def test_txt_returns_false(self, tmp_path):
        helper = AudioTagHelper()
        f = _make_file(tmp_path, "notes.txt")
        assert helper.isSupportedAudioFile(str(f)) is False

    def test_pdf_returns_false(self, tmp_path):
        helper = AudioTagHelper()
        f = _make_file(tmp_path, "booklet.pdf")
        assert helper.isSupportedAudioFile(str(f)) is False

    def test_no_extension_returns_false(self, tmp_path):
        helper = AudioTagHelper()
        f = _make_file(tmp_path, "README")
        assert helper.isSupportedAudioFile(str(f)) is False

    def test_nonexistent_file_returns_false(self, tmp_path):
        helper = AudioTagHelper()
        # Path does not exist — is_file() will return False
        assert helper.isSupportedAudioFile(str(tmp_path / "ghost.mp3")) is False

    def test_mp3_uppercase_extension_returns_false(self, tmp_path):
        helper = AudioTagHelper()
        f = _make_file(tmp_path, "track.MP3")
        # Extension comparison is case-sensitive; ".MP3" not in AUDIO_EXTENSIONS
        assert helper.isSupportedAudioFile(str(f)) is False


# ---------------------------------------------------------------------------
# T3-3: get_tags — exception handling
# ---------------------------------------------------------------------------

class TestGetTags:
    def test_returns_empty_dict_on_taglib_exception(self, tmp_path):
        helper = AudioTagHelper()
        f = _make_file(tmp_path, "bad.mp3")

        taglib_mock = sys.modules["taglib"]
        taglib_mock.File.side_effect = Exception("native error")

        result = helper.get_tags(str(f))
        assert result == {}

        # Reset side_effect so other tests are not affected
        taglib_mock.File.side_effect = None

    def test_returns_empty_dict_on_file_not_found(self, tmp_path):
        helper = AudioTagHelper()
        f = _make_file(tmp_path, "missing.mp3")

        taglib_mock = sys.modules["taglib"]
        taglib_mock.File.side_effect = FileNotFoundError("gone")

        result = helper.get_tags(str(f))
        assert result == {}

        taglib_mock.File.side_effect = None

    def test_returns_empty_dict_for_unsupported_extension(self, tmp_path):
        helper = AudioTagHelper()
        f = _make_file(tmp_path, "image.jpg")
        result = helper.get_tags(str(f))
        assert result == {}

    def test_returns_empty_dict_when_tags_is_none(self, tmp_path):
        helper = AudioTagHelper()
        f = _make_file(tmp_path, "notags.mp3")

        taglib_mock = sys.modules["taglib"]
        mock_file = MagicMock()
        mock_file.tags = None
        taglib_mock.File.side_effect = None
        taglib_mock.File.return_value = mock_file

        result = helper.get_tags(str(f))
        assert result == {}

    def test_returns_empty_dict_when_tags_is_empty(self, tmp_path):
        helper = AudioTagHelper()
        f = _make_file(tmp_path, "empty_tags.mp3")

        taglib_mock = sys.modules["taglib"]
        mock_file = MagicMock()
        mock_file.tags = {}
        taglib_mock.File.side_effect = None
        taglib_mock.File.return_value = mock_file

        result = helper.get_tags(str(f))
        assert result == {}

    def test_returns_tags_dict_when_tags_present(self, tmp_path):
        helper = AudioTagHelper()
        f = _make_file(tmp_path, "good.mp3")

        taglib_mock = sys.modules["taglib"]
        expected = {"TITLE": ["My Song"], "ARTIST": ["An Artist"]}
        mock_file = MagicMock()
        mock_file.tags = expected
        taglib_mock.File.side_effect = None
        taglib_mock.File.return_value = mock_file

        result = helper.get_tags(str(f))
        assert result == expected


# ---------------------------------------------------------------------------
# T3-4: get_release_id — extract DISCOGS_RELEASE_ID from tags
# ---------------------------------------------------------------------------

class TestGetReleaseId:
    def test_extracts_discogs_release_id(self):
        helper = AudioTagHelper()
        tags = {"DISCOGS_RELEASE_ID": ["12345678"]}
        assert helper.get_release_id(tags) == "12345678"

    def test_extracts_first_value_when_list_has_multiple(self):
        helper = AudioTagHelper()
        tags = {"DISCOGS_RELEASE_ID": ["first", "second"]}
        assert helper.get_release_id(tags) == "first"

    # -----------------------------------------------------------------------
    # T3-5: get_release_id — returns "" when tag is missing
    # -----------------------------------------------------------------------

    def test_returns_empty_string_when_tag_missing(self):
        helper = AudioTagHelper()
        tags = {"TITLE": ["Some Album"], "ARTIST": ["Some Artist"]}
        assert helper.get_release_id(tags) == ""

    def test_returns_empty_string_for_empty_tags(self):
        helper = AudioTagHelper()
        assert helper.get_release_id({}) == ""

    def test_returns_empty_string_for_none_tags(self):
        helper = AudioTagHelper()
        # get_release_id guards against None with early return ""
        assert helper.get_release_id(None) == ""


# ---------------------------------------------------------------------------
# T3-bonus: helper methods that extract other tag values
# ---------------------------------------------------------------------------

class TestTagHelpers:
    def test_get_title_returns_stripped_value(self):
        helper = AudioTagHelper()
        tags = {"TITLE": ["  Abbey Road  "]}
        assert helper.get_title(tags) == "Abbey Road"

    def test_get_title_returns_empty_when_missing(self):
        helper = AudioTagHelper()
        assert helper.get_title({}) == ""

    def test_get_title_returns_empty_for_none(self):
        helper = AudioTagHelper()
        assert helper.get_title(None) == ""

    def test_get_artist_returns_stripped_value(self):
        helper = AudioTagHelper()
        tags = {"ARTIST": [" The Beatles "]}
        assert helper.get_artist(tags) == "The Beatles"

    def test_get_artist_returns_empty_when_missing(self):
        helper = AudioTagHelper()
        assert helper.get_artist({}) == ""

    def test_get_disc_number_returns_value(self):
        helper = AudioTagHelper()
        tags = {"DISCNUMBER": ["2"]}
        assert helper.get_disc_number(tags) == "2"

    def test_get_disc_number_returns_empty_when_missing(self):
        helper = AudioTagHelper()
        assert helper.get_disc_number({}) == ""

    def test_get_track_number_returns_value(self):
        helper = AudioTagHelper()
        tags = {"TRACKNUMBER": ["7"]}
        assert helper.get_track_number(tags) == "7"

    def test_get_track_number_returns_empty_when_missing(self):
        helper = AudioTagHelper()
        assert helper.get_track_number({}) == ""
