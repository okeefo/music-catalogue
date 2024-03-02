import re, os, sys, configparser, discogs_client, requests

from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from discogs_client.models import Release
from pydantic import BaseModel
from typing import List
from mutagen import File
from mutagen.wave import WAVE
from mutagen.id3 import ID3, ID3NoHeaderError, WXXX, ID3, TIT2, APIC, TALB, TPE1, TPE2, TXXX, TDRC, TPOS, TCON, TPUB, TMED, TRCK, COMM
from file_operations.audio_tags import AudioTagHelper, AUDIO_EXTENSIONS
from ui.progress_bar_helper import ProgressBarHelper
from ui.custom_messagebox import show_message_box, ButtonType, convert_response_to_string
from log_config import get_logger
from typing import Union
from PyQt5.QtWidgets import QMessageBox

logger = get_logger("f_o.auto_tag")
__header_info = {
    "User-Agent": "YourAppName/0.1 +http://yourapp.com",
}


class TrackInfo(BaseModel):
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


class Config:
    arbitrary_types_allowed = True


class ReleaseFacade(BaseModel):
    release: Release

    class Config:
        arbitrary_types_allowed = True

    def get_id(self) -> int:
        return self.release.id

    def get_track_title(self, trackNumber: int) -> str:
        return self.release.tracklist[trackNumber].title

    def get_artist(self, trackNumber: int) -> str:
        if self.release.tracklist[trackNumber].artists:
            return self.release.tracklist[trackNumber].artists[0].name
        return self.release.data.get("artists_sort") or self.release.artists[0].name

    def get_album_artist(self) -> str:
        return self.release.data.get("artists_sort")

    def get_album(self) -> str:
        return self.release.title

    def get_catalog_number(self) -> str:
        return self.release.labels[0].data.get("catno")

    def get_country(self) -> str:
        return self.release.country

    def get_discogs_release_id(self) -> str:
        return self.release.id

    def get_genres(self) -> str:
        return ", ".join(self.release.genres)

    def get_publisher(self) -> str:
        return self.release.labels[0].name

    def get_disc_number(self, trackNumber: int) -> str:
        return self.release.tracklist[trackNumber].position

    def get_styles(self) -> str:
        return ", ".join(self.release.styles)

    def get_track_number(self, trackNumber: int) -> str:
        return str(trackNumber + 1)

    def get_url(self) -> str:
        return self.release.url

    def get_year(self) -> str:
        return self.release.data.get("released")

    def get_media(self) -> str:
        format_data = self.release.formats[0]
        media = format_data.get("name")
        descriptions = format_data.get("descriptions", [])
        description = ", ".join(desc for desc in descriptions if desc)
        return f"{media} ({description})" if description else media

    def get_track_info(self, trackNumber: int) -> TrackInfo:
        return TrackInfo(
            title=self.get_track_title(trackNumber),
            album_artist=self.__remove_brackets_and_numbers(self.get_album_artist()),
            artist=self.__remove_brackets_and_numbers(self.get_artist(trackNumber)),
            album_name=self.get_album(),
            label=self.__remove_brackets_and_numbers(self.get_publisher()),
            disc_number=self.get_disc_number(trackNumber),
            track_number=self.get_track_number(trackNumber),
            catalog_number=self.get_catalog_number(),
            discogs_id=str(self.get_discogs_release_id()),
            genres=self.get_genres(),
            url=self.get_url(),
            year=self.get_year(),
            media=self.get_media(),
            styles=self.get_styles(),
            country=self.get_country(),
        )

    def __remove_brackets_and_numbers(self, string: str):
        return re.sub(r"\(\d+\)", "", string).strip()
    
    def get_number_of_tracks(self) -> int:
        return len(self.release.tracklist)


def auto_tag_files(file_name_list: List[str], root_dir: str) -> None:
    """Auto tag files"""

    total_files = len(file_name_list)
    logger.info(f"Auto tagging {total_files} files")
    progress_bar = ProgressBarHelper(total_files, "Auto Tagging", 1)
    release_ids = __group_files_by_release_id(file_name_list, root_dir)
    user_cancelled = False

    discogs_client = get_discogs_client()
    file_count = 0

    for release_id, files in release_ids.items():
        files.sort()
        progress_bar.update_progress_bar_text(f"Auto Tagging - Release ID: {release_id}")

        release_raw = discogs_client.release(release_id)
        release = ReleaseFacade(release=release_raw)
        artwork_data = __get_cover_art_from_discogs(release_raw)

        user_cancelled, file_count = __tag_files_in_release(files, file_count, release, root_dir, artwork_data, audio_tag_helper, progress_bar)

        if user_cancelled:
            break
        

    if not user_cancelled:
        progress_bar.complete_progress_bar(total_files)


def __tag_files_in_release(
    files: List[str], file_count: int, release: ReleaseFacade, root_dir: str, artwork_data: bytes, audio_tags: AudioTagHelper, progress_bar: ProgressBarHelper
) -> Union[bool, int]:
    """Tag the files in the release."""

    user_cancelled = False
    mask = get_filename_mask_from_config()

    for file in files:
        file = os.path.join(root_dir, file)
        file_count += 1
        progress_bar.update_progress_bar(f"Auto Tagging - Release ID: {release.get_id()} - File: {file}", file_count)

        if file_track_no_match := re.search(r"(\d+)(?=\.\w+$)", file):
            file_track_no = int(file_track_no_match[1]) - 1
        else:
            logger.error(f"Failed to get track number from file: {file}")
            continue

        full_path = Path(os.path.join(root_dir, file))

        track_info = release.get_track_info(file_track_no)
        full_path = __tag_and_rename(mask, file, audio_tags, root_dir, track_info, artwork_data)

        audio_tags.log_tag_key_values(str(full_path))

        user_cancelled = progress_bar.user_has_cancelled()
        if user_cancelled:
            break

    return user_cancelled, file_count


def __tag_and_rename(mask: str, file: str, audio_tags: AudioTagHelper, root_dir: str, track_info: TrackInfo, artwork_data: bytes) -> Path:
    """Tag, add artwork and rename the file."""

    logger.info(f"Updating tags for file: {file}")
    logger.info(f"tags: {track_info.get_desc_csv()}")

    full_path = Path(os.path.join(root_dir, file))
    if full_path.suffix == ".wav":
        __add_tags_and_cover_art_to_wav_file(full_path, track_info, artwork_data)
    else:
        __add_tags_and_cover_art_to_mp3_file(full_path, track_info, artwork_data)

    return __rename_file_based_on_mask(mask, file, audio_tags, root_dir)


def __add_tags_and_cover_art_to_wav_file(wav_file: str, track_info: TrackInfo, artwork_data: bytes) -> None:
    """Add tags and cover art to the file"""

    song = __open_file_wav(wav_file)
    song.tags = __add_tags(song.tags, track_info)
    song.tags = __add_cover_art(song.tags, artwork_data, wav_file)
    song.save()


def __add_tags_and_cover_art_to_mp3_file(mp3_file: str, track_info: TrackInfo, artwork_data: bytes) -> None:
    """Add tags and cover art to the file"""
    song: ID3
    song = __open_file_mp3(mp3_file)
    song = __add_tags(song, track_info)
    song = __add_cover_art(song, artwork_data, mp3_file)
    song.save()


def tag_filename(files_to_rename: list[str], root_dir: str) -> None:
    """Get the filename mask from the config file"""

    if files_to_rename is None or not files_to_rename:
        logger.info("No files to rename")
        return

    logger.info(f"Renaming {len(files_to_rename)} files based on tags")

    msg = "This will rename the files based on the tags. Are you sure you wish to continue?"
    user_response = show_message_box(msg, ButtonType.YesNo, "Rename files based on tags", "warning")
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

    file = os.path.join(root_dir, file)
    tags = audio_tags.get_tags(file)
    new_name = __derive_new_file_name(mask, tags)
    if new_name is None:
        logger.error(f"Failed to derive new file name for file - missing tags: {file}")
        return None

    _, ext = os.path.splitext(file)
    new_name += ext

    _, new_name = os.path.split(new_name)


    try:
        new_name = re.sub(r'[<>:"/\\|?*]', '', str(new_name))
        logger.info(f"Renaming file: {file} to: {new_name}")
        full_path = Path(os.path.join(root_dir, new_name))
        # if target file skip
        if os.path.exists(full_path):
            logger.info(f"File already exists: {full_path}")
            return full_path
         
        os.rename(file, full_path)
    
    except Exception as e:
        logger.error(f"Failed to rename file: {file} to: {new_name} ", exc_info=True)


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
            return None
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


def __open_file_wav(full_path: str) -> WAVE:
    """Open wav file and return the WAVE frame. If no WAVE tag is found, create a new one."""

    song = WAVE(full_path)
    song.add_tags() if song.tags is None else song.tags.clear()
    return song


def __open_file_mp3(full_path: str) -> ID3:
    """Open mp3 file and return the ID3 frame. If no ID3 tag is found, create a new one."""
    try:
        return ID3(full_path)
    except ID3NoHeaderError:
        print(f"No ID3 tag found in {full_path}. Creating a new one.")
        ID3().save(full_path)
        return ID3(full_path)


def __add_tags(song: Union[WAVE.tags, ID3], track_info: TrackInfo) -> Union[WAVE.tags, ID3]:
    """Add tags to the file, either a WAVE or ID3 object (yup I release i'm "ducking" here - but i'm embracing it)"""
    song.add(WXXX(encoding=3, url=track_info.url))
    song.add(TIT2(encoding=3, text=track_info.title))
    song.add(TALB(encoding=3, text=track_info.album_name))
    song.add(TPE1(encoding=3, text=track_info.artist))
    song.add(TPE2(encoding=3, text=track_info.album_artist))
    song.add(TXXX(encoding=3, desc=AudioTagHelper.CATALOG_NUMBER, text=track_info.catalog_number))
    song.add(TXXX(encoding=3, desc=AudioTagHelper.DISCOGS_RELEASE_ID, text=track_info.discogs_id))
    song.add(TXXX(encoding=3, desc=AudioTagHelper.COUNTRY, text=track_info.country))
    song.add(TXXX(encoding=3, desc=AudioTagHelper.STYLE, text=track_info.styles))
    song.add(TDRC(encoding=3, text=track_info.year))
    song.add(TPOS(encoding=3, text=track_info.disc_number))
    song.add(TRCK(encoding=3, text=track_info.track_number))
    song.add(TCON(encoding=3, text=track_info.genres))
    song.add(TPUB(encoding=3, text=track_info.label))
    song.add(TMED(encoding=3, text=track_info.media))
    song.add(COMM(encoding=3, text="Tagged by oO-KeeF-Oo"))
    return song


def __get_cover_art_from_discogs(release_raw: Release) -> bytes:

    image_list = release_raw.images

    if len(image_list) > 0:

        image: dict = image_list[0]
        image_uri = image.get("uri")
        logger.info(f"getting  cover art to from: {image_uri}")
        try:
            response = requests.get(image_uri, headers=__header_info)

            if response.status_code == 200:
                return response.content

        except Exception as e:
            logger.exception(f"Failed to get cover art from: {image_uri} : {e}")

    return None


def __add_cover_art(song: Union[WAVE.tags, ID3], art_work, full_path: Path) -> None:
    """Add cover art to the file, either a WAVE or ID3 object"""

    try:
        logger.info(f"Adding cover art to file: {full_path}")
        song.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Front Cover", data=art_work))

    except Exception as e:
        logger.exception(f"Failed to add cover art to file: {full_path} : {e}")

    return song


def get_discogs_client() -> discogs_client.Client:
    """Get Discogs client"""

    logger.info("Getting Discogs client")
    config = configparser.ConfigParser()
    config.read("config.ini")
    token = config["discogs"]["token"]
    return discogs_client.Client("ExampleApplication/0.1", user_token=token)


def __group_files_by_release_id(files: List[str], root_dir: str) -> dict:
    """Group files by release id and return a dictionary with the release id as the key and the files as the value."""
    logger.info(f"Grouping {len(files)} files by release id")

    # Join the extensions in the pattern, escaping the dot
    extensions_pattern = "|".join(re.escape(ext) for ext in AUDIO_EXTENSIONS)

    release_id_pattern = re.compile(rf"r(\d+)-\d+.({extensions_pattern})$")
    release_id_to_files = {}

    for file in files:
        
        release_id = __valid_File_check(file)      
        if release_id is None:
            continue
        
        if release_id not in release_id_to_files:
            release_id_to_files[release_id] = []
        
        release_id_to_files[release_id].append(file)

    logger.info(f"Grouped {len(release_id_to_files)} release ids")
    # log the release ids
    logger.info(f"Release ids: {release_id_to_files.keys()}")
    return release_id_to_files

def __valid_File_check(file: str) -> str:
    """Check if the file is valid"""
    
    if match := re.search(r"r(\d{6,10})", file):
        release_id = match[1]
        logger.info(f"{release_id} - Found release id {release_id} in file name: {file}")
        
        # Search for a number of max two digits before the file extension
        if match := re.search(r"[-_](\d{1,2})\.\w+$", file):
            track_number = match[1]
            logger.info(f"{release_id} - Found track number {track_number} in file name: {file}")
            return release_id
        else:
            logger.warn(f"{release_id} - Could not find track number in file name, skipping: {file}")

    else:
        logger.error(f"Could not find release id in file name, skipping: {file}")
    
    return None

    

if __name__ == "__main__":
    file_list = ["a8_jam and spoon-r21478021-02.wav"]
    auto_tag_files(file_list, os.path.normpath("E:\\tmp_cop_A"))
