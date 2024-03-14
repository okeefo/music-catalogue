from pathlib import Path
from log_config import get_logger
import taglib
from mutagen.wave import WAVE
from mutagen.id3 import ID3, APIC, ID3NoHeaderError
from mutagen import File

AUDIO_EXTENSIONS = [".mp3", ".wav"]
logger = get_logger(__name__)


# The AudioTags class is used to manage and manipulate audio tags.
class AudioTagHelper:
    
    def __init__(self):
        pass
        
    def get_tags_and_cover_art(self, absolute_path_filename: str) -> tuple[dict,list[APIC]]:
        
        tags = self.get_tags(absolute_path_filename)
        cover__art = self.get_cover_art(absolute_path_filename)
        return tags, cover__art

    def get_tags(self, absolute_path_filename: str) -> dict:
        if not self.isSupportedAudioFile(absolute_path_filename):
            return {}

        try:
            tags = taglib.File(Path(absolute_path_filename)).tags

        except FileNotFoundError:
            logger.exception(f"File not found: '{absolute_path_filename}'")
            return {}

        except Exception:
            logger.exception(f"Could not read tags from: '{absolute_path_filename}'")
            return {}

        if not tags:
            logger.warning(f"No tags found in file: '{absolute_path_filename}'")
            return {}

        logger.info(f"Found tags in file: '{absolute_path_filename}' tags:'{tags}'")
        return tags
    
    # Given a collection of tags and a fully qualified filename, write the tags to the file
    def write_tags(self, absolute_path_filename: str, tags: dict) -> None:
        if not self.isSupportedAudioFile(absolute_path_filename):
            return

        try:
            file = taglib.File(absolute_path_filename)
            file.tags = tags
            file.save()
        except Exception:
            logger.exception(f"Could not write tags to file: '{absolute_path_filename}'")
            

    def isSupportedAudioFile(self, absolute_path_filename: str) -> bool:
        path = Path(absolute_path_filename)
        if path is None:
            return False

        if not path.is_file():
            return False

        return False if path.is_dir() else path.suffix in AUDIO_EXTENSIONS

    def get_cover_art(self, absolute_path_filename: str) -> list[APIC]:
        """Returns a list of APIC tags for the artwork of the file."""

        if not self.isSupportedAudioFile(absolute_path_filename):
            return None

        path = Path(absolute_path_filename)

        if path.suffix == ".wav":
            try:
                filedata = WAVE(absolute_path_filename)
                return [] if filedata.tags is None else filedata.tags.getall("APIC")
            except Exception:
                return []
        try:
            filedata = ID3(absolute_path_filename)
            return filedata.getall("APIC")
        except ID3NoHeaderError:
            return []
        
    # Given a collection of cover art, a List[APIC] data and a fully qualified filename, write the cover art to the file, using mutagen
    def write_cover_art(self, absolute_path_filename: str, cover_art: list[APIC]) -> None:
        
        if not self.isSupportedAudioFile(absolute_path_filename):
            return
        
        path = Path(absolute_path_filename)

        if path.suffix == ".wav":
            filedata = WAVE(absolute_path_filename)
            for art in cover_art:
                filedata.tags.add(art)
            filedata.save()
        
        try:
            file = ID3(absolute_path_filename)
            for art in cover_art:
                file.add(art)
            file.save()
        except Exception:
            logger.exception(f"Could not write cover art to file: '{absolute_path_filename}'")


    TITLE = "TITLE"
    ARTIST = "ARTIST"
    ALBUM = "ALBUM"
    LABEL = "LABEL"
    DISC_NUMBER = "DISCNUMBER"
    TRACK_NUMBER = "TRACKNUMBER"
    CATALOG_NUMBER = "CATALOGNUMBER"
    DISCOGS_RELEASE_ID = "DISCOGS_RELEASE_ID"
    URL = "URL"
    ALBUM_ARTIST = "ALBUMARTIST"
    YEAR = "DATE"
    GENRE = "GENRE"
    MEDIA = "MEDIA"
    STYLE = "STYLE"
    COUNTRY = "COUNTRY"

    def log_tag_key_values(self, file_path: str) -> None:

        audio = File(file_path)
        for key, value in audio.items():
            # if th ekey starts with APIC
            if key.startswith("APIC"):
                logger.info(f"{key} - {value.pprint()} type={value.type} des={value.desc} mime={value.mime} enc={value.encoding}")
            else:
                logger.info(f"{key}  - {value} ")

    def log_tags(self, file_path: str) -> None:

        audio = File(file_path)
        logger.info(f"{audio.tags} ")
        
    def get_title(self, tags: dict) -> str:
        
        if tags is None:
            return ""

        return tags[self.TITLE][0].strip() if self.TITLE in tags else ""
    
    def get_disc_number(self, tags: dict) -> str:
        
        if tags is None:
            return ""

        return tags[self.DISC_NUMBER][0] if self.DISC_NUMBER in tags else ""    

        
    def get_track_number(self, tags: dict) -> str:
        
        if tags is None:
            return ""

        return tags[self.TRACK_NUMBER][0] if self.TRACK_NUMBER in tags else "" 
    
    def get_release_id(self, tags: dict) -> str:
        
        if tags is None:
            return ""

        return tags[self.DISCOGS_RELEASE_ID][0] if self.DISCOGS_RELEASE_ID in tags else ""  


class PictureTypeDescription:
    descriptions = {
        0x00: "Other",
        0x01: "32x32 pixels 'file icon' (PNG only)",
        0x02: "Other file icon",
        0x03: "Cover (front)",
        0x04: "Cover (back)",
        0x05: "Leaflet page",
        0x06: "Media (e.g. label side of CD)",
        0x07: "Lead artist/lead performer/soloist",
        0x08: "Artist/performer",
        0x09: "Conductor",
        0x0A: "Band/Orchestra",
        0x0B: "Composer",
        0x0C: "Lyricist/text writer",
        0x0D: "Recording Location",
        0x0E: "During recording",
        0x0F: "During performance",
        0x10: "Movie/video screen capture",
        0x11: "A bright coloured fish",
        0x12: "Illustration",
        0x13: "Band/artist logotype",
        0x14: "Publisher/Studio logotype",
    }

    @classmethod
    def get_description(cls, picture_type):
        return cls.descriptions.get(picture_type, "Unknown")
