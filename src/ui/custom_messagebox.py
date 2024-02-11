from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QIcon
import qt.resources_rcc
from typing import Literal


response_mapping = {QMessageBox.Yes: "Yes", QMessageBox.No: "No", QMessageBox.YesToAll: "Yes to all", QMessageBox.NoToAll: "No to all", QMessageBox.Cancel: "Cancel"}


@staticmethod
def convert_response_to_string(response: int) -> str:
    """Converts the response code from QMessageBox to a string representation.

    Args:
        response (int): The response code.

    Returns:
        str: The string representation of the response code.
    """

    return response_mapping.get(response, "Unknown")


# ButtonType enum.  two type YesNoCancel and YesNoToAllCancel
class ButtonType(enumerate):
    YesNoCancel = 1
    YesNoToAllCancel = 2


def show_message_box(message: str, buttonType: ButtonType, title: str = "Message", icon: Literal["warning", "information"] = "warning", parent=None) -> int:
    msg_box = QMessageBox(parent)
    msg_box.setText(message)
    msg_box.setWindowTitle(title)
    headphones = QIcon(":/icons/icons/headphones.svg")
    msg_box.setWindowIcon(headphones)
    if buttonType == ButtonType.YesNoCancel:
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
    else:
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.YesToAll | QMessageBox.NoToAll | QMessageBox.Cancel)
    if icon == "warning":
        msg_box.setIcon(QMessageBox.Warning)
    else:
        msg_box.setIcon(QMessageBox.Information)

    result = msg_box.exec_()

    # If the user clicked the "x" button, treat it as if they clicked "Cancel"
    if result == QMessageBox.NoButton:
        result = QMessageBox.Cancel

    return result


# test dialog opens
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    sys.path.insert(0, "C:\\dev\\projects\\python\\music-catalogue\\src")
    app = QApplication(sys.argv)

    result = show_message_box("This is a test", ButtonType.YesNoToAllCancel, "Test Message","information")
    result = convert_response_to_string(result)
    print(f"response was {result}")
    sys.exit(result)
