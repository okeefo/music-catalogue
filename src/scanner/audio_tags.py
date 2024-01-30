from pathlib import Path
import logging
import taglib
from mutagen.wave import WAVE
from mutagen.id3 import ID3, PictureType, APIC
from tinytag import TinyTag
from PIL import Image
import io

from tinytag import TinyTagException

AUDIO_EXTENSIONS = [".mp3", ".wav"]


# The AudioTags class is used to manage and manipulate audio tags.
class AudioTags:
    logger = logging.getLogger(__name__)

    def get_tags(self, absolute_path_filename: str) -> dict:
        if not self.isSupported(absolute_path_filename):
            return {}

        try:
            tags = taglib.File(Path(absolute_path_filename)).tags

        except FileNotFoundError:
            self.logger.exception("File %s not found", absolute_path_filename)
            return {}

        except TagLibError:
            self.logger.exception("Could not read tags from %s", absolute_path_filename)
            return {}

        if not tags:
            self.logger.warning("No tags found in file %s", absolute_path_filename)
            return {}

        self.logger.info("Found tags in file %s: %s", absolute_path_filename, tags)
        return tags

    def isSupported(self, absolute_path_filename: str) -> bool:
        path = Path(absolute_path_filename)
        if path is None:
            return False

        if not path.is_file():
            return False

        if path.is_dir():
            return False

        return path.suffix in AUDIO_EXTENSIONS

    def get_cover_art(self, absolute_path_filename: str) -> list[APIC]:
        """Returns a list of APIC tags for the artwork of the file."""

        if not self.isSupported(absolute_path_filename):
            return None

        path = Path(absolute_path_filename)

        if path.suffix == ".wav":
            filedata = WAVE(absolute_path_filename)
            artwork = filedata.tags.getall("APIC")
        else:
            filedata = ID3(absolute_path_filename)
            # return artwork from mp3
            artwork = filedata.getall("APIC")

        # Create a dictionary that maps picture type numbers to descriptions
        picture_types = {value: key for key, value in vars(PictureType).items() if not key.startswith("_")}

        # loop round artwork and open (show) each image
        for tag in artwork:
            # print the mime type of the image, the PictureType as description, size in KB or MB adn ratio
            print("Picture type:", picture_types.get(tag.type, "Unknown"))
            print("Picture mime:", tag.mime)

            image_data = io.BytesIO(tag.data)
            image = Image.open(image_data)
            print(f"picture size: {image.size[0]}x{image.size[1]}")
            image_size_kb = len(tag.data) / 1024
            print("Image size: {:.2f} KB".format(image_size_kb))
            print(f"Picture desc:", tag.desc)

        # image.show()

        # No cover art found
        return artwork


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
