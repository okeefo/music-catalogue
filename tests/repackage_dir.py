import pytest
from PyQt5.QtWidgets import QApplication

from src.scanner.repackage_dir import preview_repackage
from src.scanner.scanner_dir import FileNode, FileType


@pytest.fixture(autouse=True)
def setup_qapplication():
    app = QApplication([])
    yield
    app.exit()


def test_preview_repackage_empty(mocker):
    # Arrange
    source_structure = FileNode("source", FileType.DIRECTORY)
    target_structure = FileNode("target", FileType.DIRECTORY)
    expected_structure = FileNode("target", FileType.DIRECTORY)
    expected_structure.add_child_node("repackage", FileType.DIRECTORY)
    statusbar_messages = ["Repackaging...", "Repackaging... Done"]
    test_id = "empty"

    run_test(source_structure, target_structure, expected_structure, statusbar_messages, test_id, mocker)


def run_test(source_structure, target_structure, expected_structure, statusbar_messages, test_id, mocker):
    # Arrange
    statusbar_mock = mocker.Mock()

    # Act
    result_tree = preview_repackage(source_structure, target_structure, statusbar_mock)

    # Assert
    try:
        assert result_tree == expected_structure
        statusbar_mock.assert_has_calls([mocker.call(message) for message in statusbar_messages])
    except AssertionError as e:
        raise AssertionError(f"Test '{test_id}' failed: {str(e)}") from e
