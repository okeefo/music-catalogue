import re, os, sys, configparser, discogs_client, requests

from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from discogs_client.models import Release
from typing import List
from mutagen import File
from mutagen.wave import WAVE
from mutagen.id3 import ID3, WXXX, ID3, TIT2, APIC, TALB, TPE1, TPE2, TXXX, TDRC, TPOS, TCON, TPUB, TMED, TRCK, COMM
import taglib
from file_operations.audio_tags import AudioTagHelper
from ui.progress_bar_helper import ProgressBarHelper
from ui.custom_messagebox import show_message_box, ButtonType, convert_response_to_string
from log_config import get_logger
from typing import Union
from PyQt5.QtWidgets import QMessageBox

logger = get_logger("f_o.auto_tag")


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


audio_tag_helper = AudioTagHelper()


class ReleaseFacade:

    release: Release = None

    def __init__(self, release: Release):
        self.release = release
        self.data = release.data

    def get_id(self) -> int:
        return self.release.id

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
        return str(self.data.get("uri"))

    def get_year(self) -> str:
        # return self.data.get("released_formatted")
        return self.data.get("released")

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
        """Returns a TrackInfo object for the given track number"""

        track_info = TrackInfo()
        track_info.title = self.get_track_title(trackNumber)
        track_info.album_artist = self.remove_brackets_and_numbers(self.get_album_artist())
        track_info.artist = self.remove_brackets_and_numbers(self.get_artist(trackNumber))
        track_info.album_name = self.get_album()
        track_info.label = self.remove_brackets_and_numbers(self.get_publisher())
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

    def remove_brackets_and_numbers(self, string: str):
        return re.sub(r"\(\d+\)", "", string).strip()


def auto_tag_files(file_name_list: List[str], root_dir: str) -> None:
    """Auto tag files"""

    total_files = len(file_name_list)
    logger.info(f"Auto tagging {total_files} files")
    progress_bar = ProgressBarHelper(total_files, "Auto Tagging", 0)
    release_ids = __group_files_by_release_id(file_name_list)
    user_cancelled = False

    discogs_client = __get_discogs_client()
    file_count = 0

    art = b"\x00"
    for release_id, files in release_ids.items():

        files = sorted(files)
        progress_bar.update_progress_bar_text(f"Auto Tagging - Release ID: {release_id}")

        release_raw = discogs_client.release(int(release_id[1:]))  # Remove the 'r' prefix from the release ID
        release = ReleaseFacade(release_raw)
        artwork_data = __get_cover_art_from_discogs(release_raw)

        user_cancelled, file_count = __tag_files_in_release(files, file_count, release, root_dir, artwork_data, audio_tag_helper, progress_bar)

        if user_cancelled:
            break

    if not user_cancelled:
        progress_bar.complete_progress_bar(file_count)


def __tag_files_in_release(
    files: List[str], file_count: int, release: ReleaseFacade, root_dir: str, artwork_data: bytes, audio_tags: AudioTagHelper, progress_bar: ProgressBarHelper
) -> Union[bool, int]:

    user_cancelled = False
    mask = get_filename_mask_from_config()

    for file in files:

        file_count += 1
        progress_bar.update_progress_bar(f"Auto Tagging - Release ID: {release.get_id()} - File: {file}", file_count)

        if file_track_no_match := re.search(r"(\d+)(?=\.\w+$)", file):
            file_track_no = int(file_track_no_match[1]) - 1
        else:
            logger.error(f"Failed to get track number from file: {file}")
            continue

        full_path = Path(os.path.join(root_dir, file))

        track_info = release.get_track_info(file_track_no)
        logger.info(f"Updating tags for file: {file}")
        logger.info(f"tags: {track_info.get_desc_csv()}")

        song = __open_file(full_path)

        if song.tags is None:
            song.add_tags()

        song.tags.clear()

        song = __add_tags(song, track_info)
        song = __add_cover_art(song, artwork_data, full_path)
        song.save()

        full_path = __rename_file_based_on_mask(mask, file, audio_tags, root_dir)

        audio_tags.log_tag_key_values(str(full_path))

        user_cancelled = progress_bar.user_has_cancelled()
        if user_cancelled:
            break

    return user_cancelled, file_count


def tag_filename(files_to_rename: list[str], root_dir: str) -> None:
    """Get the filename mask from the config file"""

    if files_to_rename is None or not files_to_rename:
        logger.info("No files to rename")
        return

    logger.info(f"Renaming {len(files_to_rename)} files based on tags")

    msg = "This will rename the files based on the tags. Are you sure you wish to continue?"
    user_response = QMessageBox.question(None, "Rename files based on tags", msg, QMessageBox.Yes | QMessageBox.No)
    logger.info(f"User response: {convert_response_to_string(user_response)}")
    if user_response == QMessageBox.No:
        return

    mask = get_filename_mask_from_config()
    progress = ProgressBarHelper(len(files_to_rename), "Renaming files based on tags", 0)

    for i, file in enumerate(files_to_rename):
        full_path = Path(os.path.join(root_dir, file))

        progress.update_progress_bar_text(f"Renaming file: {file}")

        if os.path.isdir(full_path) or not audio_tag_helper.isSupportedAudioFile(full_path):
            logger.info(f"Skipping file reason=UnsupportedFileExtension: {full_path}")
        else:
            __rename_file_based_on_mask(mask, file, audio_tag_helper, root_dir)

        progress.update_progress_bar_value(i + 1)


def __rename_file_based_on_mask(mask, file, audio_tags: AudioTagHelper, root_dir: str) -> str:
    """Rename the file based on the mask and tags"""

    tags = audio_tags.get_tags(file)
    new_name = __derive_new_file_name(mask, tags)

    _, ext = os.path.splitext(file)
    new_name += ext

    full_path = Path(os.path.join(root_dir, new_name))

    logger.info(f"Renaming file: {file} to: {new_name}")

    try:
        os.rename(file, full_path)

    except Exception as e:

        logger.error(f"Failed to rename file: {file} to: {new_name}")
        logger.error(e.with_traceback)

    return full_path


def __derive_new_file_name(mask: str, tags: dict) -> str:
    """Derive the new file name from the mask and tags"""
    new_name = mask
    mask_tags = re.findall(r"%(\w+)%", mask)
    for tag in mask_tags:

        new_tag = __get_mapping_for_tag(tag)
        if new_tag in tags and tags[new_tag]:
            new_name = new_name.replace(f"%{tag}%", tags[new_tag][0])
        else:
            new_name = new_name.replace(f"%{tag}%", tag)
    return new_name


tag_mapping = {
    "catalognumber": AudioTagHelper.CATALOG_NUMBER,
    "publisher": AudioTagHelper.LABEL,
    "album": AudioTagHelper.ALBUM,
    "discnumber": AudioTagHelper.DISC_NUMBER,
    "artist": AudioTagHelper.ARTIST,
    "title": AudioTagHelper.TITLE,
}


def __get_mapping_for_tag(tag: str) -> str:
    """Get the mapping for the tag"""
    return tag_mapping[tag.lower()] if tag.lower() in tag_mapping else ""


def get_filename_mask_from_config() -> str:
    """Get the filename mask from the config file"""
    config = configparser.RawConfigParser()
    config.read("config.ini")
    return config.get("autotag", "filename_mask")


def __open_file(full_path: str) -> File:
    """Open file"""
    return WAVE(full_path) if full_path.suffix == ".wav" else ID3(full_path)


def __add_tags(song: File, track_info: TrackInfo) -> File:

    song.tags.add(WXXX(encoding=3, url=track_info.url))
    song.tags.add(TIT2(encoding=3, text=track_info.title))
    song.tags.add(TALB(encoding=3, text=track_info.album_name))
    song.tags.add(TPE1(encoding=3, text=track_info.artist))
    song.tags.add(TPE2(encoding=3, text=track_info.album_artist))
    song.tags.add(TXXX(encoding=3, desc=AudioTagHelper.CATALOG_NUMBER, text=track_info.catalog_number))
    song.tags.add(TXXX(encoding=3, desc=AudioTagHelper.DISCOGS_RELEASE_ID, text=track_info.discogs_id))
    song.tags.add(TXXX(encoding=3, desc=AudioTagHelper.COUNTRY, text=track_info.country))
    song.tags.add(TXXX(encoding=3, desc=AudioTagHelper.STYLE, text=track_info.styles))
    song.tags.add(TDRC(encoding=3, text=track_info.year))
    song.tags.add(TPOS(encoding=3, text=track_info.disc_number))
    song.tags.add(TRCK(encoding=3, text=track_info.track_number))
    song.tags.add(TCON(encoding=3, text=track_info.genres))
    song.tags.add(TPUB(encoding=3, text=track_info.label))
    song.tags.add(TMED(encoding=3, text=track_info.media))
    song.tags.add(COMM(encoding=3, text="Tagged by oO-KeeF-Oo"))
    return song


def __get_cover_art_from_discogs(release_raw: Release) -> bytes:

    image_list = release_raw.images

    if len(image_list) > 0:
        # Headers for the request
        header_info = {
            "User-Agent": "YourAppName/0.1 +http://yourapp.com",
        }

        image = image_list[0]
        image_uri = image.get("uri")
        logger.info(f"getting  cover art to from: {image_uri}")
        try:
            response = requests.get(image_uri, headers=header_info)

            if response.status_code == 200:
                return response.content

        except Exception as e:
            logger.exception(f"Failed to get cover art from: {image_uri} : {e}")

    return None


def __add_cover_art(song: File, art_work, full_path: Path) -> None:
    """Add cover art to the file"""

    try:
        logger.info(f"Adding cover art to file: {full_path}")
        # artwork_data = b'\x00'
        song.tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Front Cover", data=art_work))

    except Exception as e:
        logger.exception(f"Failed to add cover art to file: {full_path} : {e}")

    return song


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

    # file_list = ["a8_jam and spoon-r21478021-01.wav", "a8_jam and spoon-r21478021-02.wav"]
    file_list = ["a8_jam and spoon-r21478021-02.wav"]
    # file_list = ["MiTM - NASTY'ER EP - A1-r15174933-01.wav", "MiTM - NASTY'ER EP - A2-r15174933-02.wav"]

    #   file_list = ["TheRave--A1--r28675504-01.wav"]

    auto_tag_files(file_list, os.path.normpath("E:\\tmp_cop_A"))
