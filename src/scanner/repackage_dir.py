
from scanner import scanner_dir

def preview_repackage(tree_structure_source, tree_structure_target, update_statusbar):
    
    new_tree = tree_structure_target.copy()
    new_tree.add_child_node("repackage", scanner_dir.DIRECTORY)
    return new_tree


