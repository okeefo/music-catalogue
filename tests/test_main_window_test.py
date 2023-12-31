import unittest
from PyQt5.QtWidgets import QApplication, QAction, QFileDialog
from unittest.mock import patch
from src.main_window import MainWindow
from unittest.mock import MagicMock

class TestMainWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = MagicMock()  # Use MagicMock instead of QApplication
        cls.window = MainWindow(cls.app)

    @classmethod
    def tearDownClass(cls):
        cls.window.close()
        cls.app.quit()
    
    def test_setup_exit(self):
        action_exit = self.window.findChild(QAction, "mf_exit")
        self.assertIsNotNone(action_exit)
        with patch.object(self.app, "quit") as mock_quit:
            action_exit.triggered.connect(mock_quit)
            action_exit.triggered.emit()
            mock_quit.assert_called_once()

    def test_setup_scan(self):
        action_scan = self.window.findChild(QAction, "mf_scan")
        self.assertIsNotNone(action_scan)
        with patch.object(
            QFileDialog, "getExistingDirectory", return_value="/path/to/directory"
        ):
            with patch.object(self.window, "update_status") as mock_update_status:
                with patch.object(
                    self.window, "update_statusbar"
                ) as mock_update_statusbar:
                    action_scan.triggered.emit()
                    mock_update_status.assert_called_once_with(
                        "Scanning directory: /path/to/directory"
                    )
                    mock_update_statusbar.assert_called_once_with(
                        "Scanning directory: /path/to/directory"
                    )


if __name__ == "__main__":
    unittest.main()
