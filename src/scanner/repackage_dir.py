from src.scanner import scanner_dir


def preview_repackage(tree_structure_source, tree_structure_target, update_statusbar):
    update_statusbar("Repackaging...")
    new_tree = tree_structure_target.copy()
    new_tree.add_child_node("repackage", scanner_dir.FileType.DIRECTORY)
    update_statusbar("Repackaging... Done")
    return new_tree
