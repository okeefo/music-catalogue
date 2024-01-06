import pytest
from PyQt5.QtWidgets import QApplication
from unittest.mock import MagicMock, patch
from src.main_window import MainWindow
from PyQt5.QtWidgets import QMessageBox
from unittest.mock import patch

@pytest.fixture(scope="module")
def app():
    app_mock = MagicMock()
    app_mock.quit = MagicMock()
    return app_mock

@pytest.fixture
def main_window(app):
    return MainWindow(app)

@pytest.fixture
def mock_message_box(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr('PyQt5.QtWidgets.QMessageBox', mock)
    return mock

@pytest.fixture
def mock_file_dialog(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr('PyQt5.QtWidgets.QFileDialog', mock)
    return mock

@pytest.fixture
def mock_get_dir_structure(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr('src.scanner.scanner_dir.get_dir_structure', mock)
    return mock

# Happy path tests



@pytest.mark.parametrize("user_response, expected_quit_call_count", [
    (QMessageBox.Yes, 1), # ID: confirm-exit-yes
    (QMessageBox.No, 0),  # ID: confirm-exit-no
])
@patch('PyQt5.QtWidgets.QMessageBox.question')
def test_confirm_exit(mock_question, main_window, user_response, expected_quit_call_count):
    # Arrange
    mock_question.return_value = user_response

    # Act
    main_window.confirm_exit()

    # Assert
    assert main_window.app.quit.call_count() == expected_quit_call_count


@pytest.mark.parametrize("directory, type", [
    ("C:\\Music", "source"), # ID: scan-dir-happy-path-source
    ("D:\\Videos", "target"), # ID: scan-dir-happy-path-target
])
def test_scan_directory(main_window, mock_get_dir_structure, mock_message_box, directory, type):
    # Arrange
    mock_get_dir_structure.return_value = MagicMock(name=directory)

    # Act
    main_window.scan_directory(directory, MagicMock(), type)

    # Assert
    mock_get_dir_structure.assert_called_once_with(directory, main_window.update_statusbar)
    assert getattr(main_window, f"tree_structure_{type}").name == directory

# Edge cases

@pytest.mark.parametrize("directory, type", [
    ("", "source"), # ID: scan-dir-empty-source
    ("", "target"), # ID: scan-dir-empty-target
])
def test_scan_directory_empty(main_window, mock_get_dir_structure, directory, type):
    # Act
    main_window.scan_directory(directory, MagicMock(), type)

    # Assert
    mock_get_dir_structure.assert_not_called()

# Error cases

@pytest.mark.parametrize("directory, type, exception", [
    ("C:\\InvalidPath", "source", Exception("Invalid path")), # ID: scan-dir-exception-source
    ("D:\\InvalidPath", "target", Exception("Invalid path")), # ID: scan-dir-exception-target
])
def test_scan_directory_exception(main_window, mock_get_dir_structure, mock_message_box, directory, type, exception):
    # Arrange
    mock_get_dir_structure.side_effect = exception

    # Act
    with pytest.raises(Exception):
        main_window.scan_directory(directory, MagicMock(), type)

    # Assert
    mock_message_box.critical.assert_called_once()
