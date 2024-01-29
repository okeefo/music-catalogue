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
        
        path = Path(absolute_path_filename)

        if not self.isSupported(path):
            return {}

        try:
            tags = taglib.File(path).tags


        except FileNotFoundError:
            self.logger.exception("File %s not found", path)
            return {}

            
        except FileNotFoundError:
            self.logger.exception("File %s not found", path)
            return {}

        except TagLibError:
            self.logger.exception("Could not read tags from %s", path)
            return {}

        if not tags:
            self.logger.warning("No tags found in file %s", path)
            return {}

        self.logger.info("Found tags in file %s: %s", path, tags)
        return tags

    def isSupported(self, absolute_path_filename: str) -> bool:
       
        return self.isSupported(Path(absolute_path_filename))
    
    def isSupported(self, path: Path) -> bool:
       
        if path is None:
            return False

        if not path.is_file():
            return False

        if path.is_dir():
            return False

        return path.suffix in AUDIO_EXTENSIONS
    

    def get_cover_art(self, absolute_path_filename: str) -> list[APIC]:
        """ Returns a list of APIC tags for the artwork of the file. """
        
        path = Path(absolute_path_filename)
        if not self.isSupported(path):
            return None
        
        if path.suffix == ".wav":
            filedata = WAVE(absolute_path_filename)
            artwork = filedata.tags.getall('APIC')
        else:
            filedata = ID3(absolute_path_filename)
            #return artwork from mp3
            artwork = filedata.getall("APIC")
            
        # Create a dictionary that maps picture type numbers to descriptions
        picture_types = {value: key for key, value in vars(PictureType).items() if not key.startswith('_')}
            
        #loop round artwork and open (show) each image
        for tag in artwork:
            #print the mime type of the image, the PictureType as description, size in KB or MB adn ratio
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
        return artwork;  
