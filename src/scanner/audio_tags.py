from pathlib import Path
import logging
import taglib
#from taglib import TagLibError

AUDIO_EXTENSIONS = [".mp3", ".wav"] 

# The AudioTags class is used to manage and manipulate audio tags.
class AudioTags:
    
    logger = logging.getLogger(__name__)

    def get_tags(self, absolute_path_filename: str) -> dict:
        
        path = Path(absolute_path_filename)

        if not path.is_file():
            self.logger.error("Path %s does not exist or is not a file", path)
            return {}

        if path.is_dir():
            self.logger.error("Path %s is a directory", path)
            return {}

        if path.suffix not in AUDIO_EXTENSIONS:
            self.logger.error("File %s has an unsupported audio extension", path)
            return {}

        try:
            tags = taglib.File(path).tags

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
    

