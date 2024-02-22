import re, os, sys
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import discogs_client
import configparser
import requests
from discogs_client.models import Release, Master
import taglib


from typing import List
from file_operations.audio_tags import AudioTags

from log_config import get_logger
import mutagen
from discogs_client.models import Release

logger = get_logger("f_o.auto_tag")


def auto_tag_files(file_name_list: List[str], root_dir: str) -> None:
    """Auto tag files"""
    logger.info(f"Auto tagging {len(file_name_list)} files")
    release_ids = __group_files_by_release_id(file_name_list)

    # Initialize Discogs client
    d = __get_discogs_client()

    for release_id, files in release_ids.items():
        # Sort the files
        files = sorted(files)

        release_raw = d.release(int(release_id[1:]))  # Remove the 'r' prefix from the release ID
        release = ReleaseFacade(release_raw)

        # Update tags for each file
        for i, file in enumerate(files):
            full_path = os.path.join(root_dir, file)
            song = taglib.File(Path(full_path))

            track_info = release.get_track_info(i)
            logger.info(f"Updating tags for file: {file}")
            logger.info(f"tags: {track_info.get_desc_csv()}")

            song.tags[AudioTags.TITLE] = [track_info.title]
            song.tags[AudioTags.ALBUM_ARTIST] = [track_info.album_artist]
            song.tags[AudioTags.ARTIST] = [track_info.artist]
            song.tags[AudioTags.ALBUM] = [track_info.album_name]
            song.tags[AudioTags.LABEL] = [track_info.label]
            song.tags[AudioTags.DISC_NUMBER] = [track_info.disc_number]
            song.tags[AudioTags.TRACK_NUMBER] = [track_info.track_number]
            song.tags[AudioTags.CATALOG_NUMBER] = [track_info.catalog_number]
            song.tags[AudioTags.DISCOGS_RELEASE_ID] = [track_info.discogs_id]
            song.tags[AudioTags.GENRE] = [track_info.genres]
            song.tags[AudioTags.URL] = [track_info.url]
            song.tags[AudioTags.YEAR] = [track_info.year]
            song.tags[AudioTags.MEDIA] = [track_info.media]
            song.tags[AudioTags.STYLE] = [track_info.styles]
            song.tags[AudioTags.COUNTRY] = [track_info.country]

            song.save()

class TrackInfo:
    title: str = None
    album_artist: str = None
    artist: str = None
    album_name: str = None
    label: str = None
    disc_number: str = None
    track_number: str = None
    catalog_number: str = None
    discogs_id: str = None
    genres: str = None
    year: str = None
    media: str = None
    styles: str = None
    url: str = None
    country: str = None

    def get_desc_csv(self) -> str:
        return f"title:{self.title}, album_artist:{self.album_artist}, artist:{self.artist}, album_name:{self.album_name}, label:{self.label}, disc_no:{self.disc_number}, tack_no:{self.track_number}, catno:{self.catalog_number}, id:{self.discogs_id}, genres:{self.genres}, year:{self.year}, media:{self.media}, styles:{self.styles}, country:{self.country}, url:{self.url}"


class ReleaseFacade:

    release: Release = None

    def __init__(self, release: Release):
        self.release = release
        self.data = release.data

    def get_track_title(self, trackNumber: int) -> str:
        return self.release.tracklist[trackNumber].title

    def get_artist(self, trackNumber: int) -> str:
        # first check if there is an artist at the track level
        if self.release.tracklist[trackNumber].artists:
            return self.release.tracklist[trackNumber].artists[0].name
        if self.data.get("artists_sort"):
            return self.data.get("artists_sort")
        return self.release.artists[0].name

    def get_album_artist(self) -> str:
        return self.data.get("artists_sort")

    def get_album(self) -> str:
        return self.release.title

    def get_catalog_number(self) -> str:
        return self.data.get("labels")[0].get("catno")

    def get_country(self) -> str:
        return self.release.country

    def get_discogs_release_id(self) -> str:
        return str(self.release.id)

    def get_genres(self) -> str:
        """return a csv list of genres"""

        if len(self.release.genres) > 1:
            return ", ".join(self.release.genres)

        return self.release.genres[0] if len(self.release.genres) == 1 else ""

    def get_publisher(self) -> str:
        return self.release.labels[0].name

    def get_disc_number(self, trackNumber: int) -> str:
        return self.release.tracklist[trackNumber].position

    def get_styles(self) -> str:
        # return a csv list of styles
        if len(self.release.styles) > 1:
            return ", ".join(self.release.styles)

        return self.release.styles[0] if len(self.release.styles) == 1 else ""

    def get_track_number(self, trackNumber: int) -> str:
        return str(trackNumber + 1)

    def get_url(self) -> str:
        return self.data.get("uri")

    def get_year(self) -> str:
        return self.data.get("released_formatted")

    def get_media(self) -> str:

        media = self.data.get("formats")[0].get("name")
        if "Vinyl" in media:
            description = ""
            if len(self.data.get("formats")[0].get("descriptions")) > 1:
                for i in self.data.get("formats")[0].get("descriptions"):
                    if description != "":
                        description += ", "
                    description += i

            if description != "":
                media += f" ({description})"

        return media

    def get_track_info(self, trackNumber: int) -> TrackInfo:
        """ Returns a TrackInfo object for the given track number """

        track_info = TrackInfo()
        track_info.title = self.get_track_title(trackNumber)
        track_info.album_artist = self.get_album_artist()
        track_info.artist = self.get_artist(trackNumber)
        track_info.album_name = self.get_album()
        track_info.label = self.get_publisher()
        track_info.disc_number = self.get_disc_number(trackNumber)
        track_info.track_number = self.get_track_number(trackNumber)
        track_info.catalog_number = self.get_catalog_number()
        track_info.discogs_id = self.get_discogs_release_id()
        track_info.genres = self.get_genres()
        track_info.url = self.get_url()
        track_info.year = self.get_year()
        track_info.media = self.get_media()
        track_info.styles = self.get_styles()
        track_info.country = self.get_country() 
        return track_info


def __get_discogs_client() -> discogs_client.Client:
    """Get Discogs client"""
    logger.info("Getting Discogs client")
    config = configparser.ConfigParser()
    config.read("config.ini")
    token = config["discogs"]["token"]
    return discogs_client.Client("ExampleApplication/0.1", user_token=token)


def __group_files_by_release_id(files: List[str]) -> dict:
    """Group files by release id"""

    logger.info(f"Grouping {len(files)} files by release id")

    release_id_pattern = re.compile(r"r(\d+)-\d+\.wav$")
    release_id_to_files = {}

    for file in files:
        if match := release_id_pattern.search(file):
            release_id = f"r{match[1]}"
            logger.info(f"Found release id '{release_id}' in file '{file}'")

            if release_id not in release_id_to_files:
                release_id_to_files[release_id] = []
            release_id_to_files[release_id].append(file)

    logger.info(f"Grouped {len(release_id_to_files)} release ids")
    # log the release ids
    logger.info(f"Release ids: {release_id_to_files.keys()}")
    return release_id_to_files


if __name__ == "__main__":
    # Add the root directory of your project to the Python path

    file_list = ["a8_jam and spoon-r21478021-01.wav", "a8_jam and spoon-r21478021-02.wav"]
    #   file_list = [
    #       "MiTM - NASTY'ER EP - A1-r15174933-01.wav",
    #       "MiTM - NASTY'ER EP - A2-r15174933-02.wav"
    #   ]

    #   file_list = ["TheRave--A1--r28675504-01.wav"]
    auto_tag_files(file_list, os.path.normpath("E:\\tmp_cop_A"))
