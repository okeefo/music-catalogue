from pathlib import Path
import logging
import taglib
from mutagen.wave import WAVE 
from mutagen.id3 import ID3, PictureType
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
    
    def get_cover_art_front3(self, absolute_path_filename: str):
        
        path = Path(absolute_path_filename)
        if not self.isSupported(path):
            return None
        
        if path.suffix == ".wav":
            filedata = WAVE(absolute_path_filename)
            artwork = filedata.tags.getall('APIC')[0].data
        else:
            filedata = ID3(absolute_path_filename)
            #return artwork from mp3
            artwork = filedata.getall("APIC")[0].data
            
       # metadata = mutagen.File(filename)
#        for tag in filedata.tags.values():
 #           if tag.FrameID == 'APIC':
                    
        return artwork
             

    def get_cover_art_front(self, absolute_path_filename: str):
        
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
            
            image.show()

        # No cover art found
        return []  
    
    def get_cover_art_front4(self, absolute_path_filename: str):

        filedata = WAVE(absolute_path_filename)
        
        
       # metadata = mutagen.File(filename)
        for tag in filedata.tags.values():
            if tag.FrameID == 'APIC':
                    image_data = io.BytesIO(tag.data)
                    image = Image.open(image_data)
                    image.show()
             

        # No cover art found
        return []
    
    def get_cover_art_front2(self, absolute_path_filename: str):
        try:
            tag = TinyTag.get(absolute_path_filename, image=True)

            if tag.get_image():
                image_data = io.BytesIO(tag.get_image())
                image = Image.open(image_data)
                image.show()
            else:
                print("No cover art found")
        except TinyTagException as e:
            print("Unable to read audio file:", e)

            # No cover art found
            return None
    
    def get_cover_art_all(self, absolute_path_filename: str) -> list:
        # Get the tags using tinytag
        try:
            tags = TinyTag.get(absolute_path_filename)
        except TinyTagException:
            self.logger.warning("File %s is not a supported audio file format", absolute_path_filename)
            return []

        # Check if the file has cover art
        if hasattr(tags, 'picture') and tags.picture:
            return [tags.picture]
        else:
            self.logger.warning("File %s does not have cover art", absolute_path_filename)
            return []
        
    def get_cover_art_all_2(self, absolute_path_filename: str) -> list:
        # Get the ID3 tags using mutagen
        id3_tags = ID3(absolute_path_filename)

        # Find the cover art
        cover_arts = []
        for frame in id3_tags.values():
            if frame.FrameID == "APIC":  # APIC is the frame ID for attached picture
                cover_arts.append(frame.data)

        return cover_arts
