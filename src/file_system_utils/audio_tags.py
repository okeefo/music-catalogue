from pathlib import Path
from log_config import get_logger
import taglib
from mutagen.wave import WAVE
from mutagen.id3 import ID3,  APIC

AUDIO_EXTENSIONS = [".mp3", ".wav"]
logger = get_logger(__name__)

# The AudioTags class is used to manage and manipulate audio tags.
class AudioTags:


    def get_tags(self, absolute_path_filename: str) -> dict:
        if not self.isSupported(absolute_path_filename):
            return {}

        try:
            tags = taglib.File(Path(absolute_path_filename)).tags

        except FileNotFoundError:
            logger.exception(f"File not found: '{absolute_path_filename}'")
            return {}

        except TagLibError:
            logger.exception(f"Could not read tags from: '{absolute_path_filename}'")
            return {}

        if not tags:
            logger.warning(f"No tags found in file: '{absolute_path_filename}'")
            return {}

        logger.info(f"Found tags in file: '{absolute_path_filename}' tags:'{tags}'")
        return tags

    def isSupported(self, absolute_path_filename: str) -> bool:
        path = Path(absolute_path_filename)
        if path is None:
            return False

        if not path.is_file():
            return False

        return False if path.is_dir() else path.suffix in AUDIO_EXTENSIONS

    def get_cover_art(self, absolute_path_filename: str) -> list[APIC]:
        """Returns a list of APIC tags for the artwork of the file."""

        if not self.isSupported(absolute_path_filename):
            return None

        path = Path(absolute_path_filename)

        if path.suffix == ".wav":
            filedata = WAVE(absolute_path_filename)
            return filedata.tags.getall("APIC")
        else:
            filedata = ID3(absolute_path_filename)
            return filedata.getall("APIC")


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
