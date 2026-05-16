"""
Tests for ReleaseFacade in file_operations/auto_tag.py.

conftest.py stubs out discogs_client, discogs_client.models, requests,
ui.progress_bar_helper, config_manager, PyQt5, mutagen, taglib, and
log_config before any module is imported, so no network calls or native
extensions are triggered.

All tests use MagicMock to build a fake `release` object and wrap it in a
ReleaseFacade — no Discogs API is contacted.
"""

from unittest.mock import MagicMock

from file_operations.auto_tag import ReleaseFacade

# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_release(**attrs):
    """Return a MagicMock release with the given attributes set."""
    release = MagicMock()
    for key, value in attrs.items():
        setattr(release, key, value)
    return release


def _make_facade(**release_attrs) -> ReleaseFacade:
    """Return a ReleaseFacade wrapping a MagicMock release.

    Uses model_construct to skip Pydantic validation (the Release type is
    mocked, so the validator would reject it).
    """
    release = _make_release(**release_attrs)
    return ReleaseFacade.model_construct(release=release)


def _make_track(artists=None, title="Track Title", position="A1"):
    """Return a MagicMock that quacks like a discogs Track."""
    track = MagicMock()
    track.artists = artists if artists is not None else []
    track.title = title
    track.position = position
    return track


def _make_facade_with_tracklist(tracks, artists_sort=None, release_artists=None):
    """Return a ReleaseFacade whose release has a real tracklist."""
    release = _make_release(
        tracklist=tracks,
        data={"artists_sort": artists_sort},
        artists=release_artists if release_artists is not None else [],
    )
    return ReleaseFacade.model_construct(release=release)


# ===========================================================================
# get_artist
# ===========================================================================

class TestGetArtist:
    """ReleaseFacade.get_artist(trackNumber)"""

    def test_returns_track_artist_when_track_has_artists(self):
        artist = MagicMock()
        artist.name = "Orbital"
        track = _make_track(artists=[artist])
        facade = _make_facade_with_tracklist([track])
        assert facade.get_artist(0) == "Orbital"

    def test_falls_back_to_artists_sort_when_track_has_no_artists(self):
        """artists_sort from release.data is the first fallback."""
        track = _make_track(artists=[])
        facade = _make_facade_with_tracklist([track], artists_sort="Aphex Twin")
        assert facade.get_artist(0) == "Aphex Twin"

    def test_returns_empty_string_when_no_artists_and_no_artists_sort(self):
        """When track has no artists and there is no artists_sort, return ''."""
        track = _make_track(artists=[])
        facade = _make_facade_with_tracklist(
            [track], artists_sort=None, release_artists=[]
        )
        assert facade.get_artist(0) == ""

    def test_falls_back_to_release_artists_when_no_artists_sort(self):
        """release.artists is the second fallback when artists_sort is absent."""
        track = _make_track(artists=[])
        release_artist = MagicMock()
        release_artist.name = "Daft Punk"
        facade = _make_facade_with_tracklist(
            [track], artists_sort=None, release_artists=[release_artist]
        )
        assert facade.get_artist(0) == "Daft Punk"


# ===========================================================================
# get_catalog_number
# ===========================================================================

class TestGetCatalogNumber:
    """ReleaseFacade.get_catalog_number()"""

    def test_returns_empty_string_when_labels_is_empty(self):
        facade = _make_facade(labels=[])
        assert facade.get_catalog_number() == ""

    def test_returns_catno_from_first_label(self):
        label = MagicMock()
        label.data = {"catno": "WARP123"}
        facade = _make_facade(labels=[label])
        assert facade.get_catalog_number() == "WARP123"

    def test_returns_empty_string_when_catno_key_absent(self):
        label = MagicMock()
        label.data = {}
        facade = _make_facade(labels=[label])
        assert facade.get_catalog_number() == ""


# ===========================================================================
# get_genres
# ===========================================================================

class TestGetGenres:
    """ReleaseFacade.get_genres()"""

    def test_returns_empty_string_when_genres_is_none(self):
        facade = _make_facade(genres=None)
        assert facade.get_genres() == ""

    def test_returns_empty_string_when_genres_is_empty_list(self):
        facade = _make_facade(genres=[])
        assert facade.get_genres() == ""

    def test_joins_multiple_genres_with_comma(self):
        facade = _make_facade(genres=["Electronic", "Ambient"])
        assert facade.get_genres() == "Electronic, Ambient"

    def test_returns_single_genre_unchanged(self):
        facade = _make_facade(genres=["Techno"])
        assert facade.get_genres() == "Techno"


# ===========================================================================
# get_publisher
# ===========================================================================

class TestGetPublisher:
    """ReleaseFacade.get_publisher()"""

    def test_returns_empty_string_when_labels_is_empty(self):
        facade = _make_facade(labels=[])
        assert facade.get_publisher() == ""

    def test_returns_label_name_from_first_label(self):
        label = MagicMock()
        label.name = "Warp Records"
        facade = _make_facade(labels=[label])
        assert facade.get_publisher() == "Warp Records"


# ===========================================================================
# get_media
# ===========================================================================

class TestGetMedia:
    """ReleaseFacade.get_media()"""

    def test_returns_empty_string_when_formats_is_empty_list(self):
        facade = _make_facade(formats=[])
        assert facade.get_media() == ""

    def test_returns_empty_string_when_formats_is_none(self):
        facade = _make_facade(formats=None)
        assert facade.get_media() == ""

    def test_returns_format_name_when_no_descriptions(self):
        facade = _make_facade(formats=[{"name": "Vinyl", "descriptions": []}])
        assert facade.get_media() == "Vinyl"

    def test_returns_format_name_with_descriptions_in_parentheses(self):
        facade = _make_facade(formats=[{"name": "Vinyl", "descriptions": ['12"', "45 RPM"]}])
        assert facade.get_media() == 'Vinyl (12", 45 RPM)'

    def test_returns_format_name_when_descriptions_key_absent(self):
        facade = _make_facade(formats=[{"name": "CD"}])
        assert facade.get_media() == "CD"


# ===========================================================================
# get_country
# ===========================================================================

class TestGetCountry:
    """ReleaseFacade.get_country()"""

    def test_returns_empty_string_when_country_is_none(self):
        facade = _make_facade(country=None)
        assert facade.get_country() == ""

    def test_returns_country_string(self):
        facade = _make_facade(country="Germany")
        assert facade.get_country() == "Germany"


# ===========================================================================
# get_styles
# ===========================================================================

class TestGetStyles:
    """ReleaseFacade.get_styles()"""

    def test_returns_empty_string_when_styles_is_none(self):
        facade = _make_facade(styles=None)
        assert facade.get_styles() == ""

    def test_returns_string_unchanged_when_styles_is_a_string(self):
        facade = _make_facade(styles="Acid House")
        assert facade.get_styles() == "Acid House"

    def test_joins_list_styles_with_comma(self):
        facade = _make_facade(styles=["Acid House", "Deep House"])
        assert facade.get_styles() == "Acid House, Deep House"

    def test_joins_tuple_styles_with_comma(self):
        facade = _make_facade(styles=("Techno", "Industrial"))
        assert facade.get_styles() == "Techno, Industrial"

    def test_returns_empty_string_for_empty_list(self):
        facade = _make_facade(styles=[])
        assert facade.get_styles() == ""
