from tinytag import TinyTag

def get_publisher(file_path):
    tag = TinyTag.get(file_path)
    return tag.publisher