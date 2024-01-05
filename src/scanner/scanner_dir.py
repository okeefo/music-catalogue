import os

def create_tree(path, type):
    return {"name": os.path.basename(path), "type": type, "children": []}

def get_dir_structure(path, update_statusbar):
    tree = create_tree(path, "directory")

    if os.path.isdir(path):
        for filename in os.listdir(path):
            child_path = os.path.join(path, filename)

            if os.path.isdir(child_path):
                update_statusbar("scanning dir: " + child_path)
                tree["children"].append(get_dir_structure(child_path, update_statusbar))
            else:
                # Update the status bar with the file name
                update_statusbar("adding file: " + child_path)
                tree["children"].append(create_tree(child_path, "file"))

    return tree