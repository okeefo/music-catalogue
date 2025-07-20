import sys
from PyQt5.QtWidgets import QApplication, QTreeView, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtGui import QStandardItemModel, QStandardItem

def create_model():
    # Create a model with three columns
    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(['Column 1', 'Column 2', 'Column 3'])

    # Create first parent item and its columns
    parent1 = QStandardItem('Parent 1')
    parent1_col2 = QStandardItem('Data 1-2')
    parent1_col3 = QStandardItem('Data 1-3')
    # Append a child row with three columns
    child1 = [QStandardItem('Child 1-1'),
              QStandardItem('Child 1-2'),
              QStandardItem('Child 1-3')]
    parent1.appendRow(child1)
    # Append the parent row to the model
    model.appendRow([parent1, parent1_col2, parent1_col3])

    # Create second parent item with a child
    parent2 = QStandardItem('Parent 2')
    parent2_col2 = QStandardItem('Data 2-2')
    parent2_col3 = QStandardItem('Data 2-3')
    child2 = [QStandardItem('Child 2-1'),
              QStandardItem('Child 2-2'),
              QStandardItem('Child 2-3')]
    parent2.appendRow(child2)
    model.appendRow([parent2, parent2_col2, parent2_col3])

    return model

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QTreeView Multi‑Column Example")
        central = QWidget(self)
        layout = QVBoxLayout(central)

        # Create and set up the QTreeView
        self.tree_view = QTreeView()
        self.tree_view.setModel(create_model())
        self.tree_view.expandAll()  # expand all nodes

        layout.addWidget(self.tree_view)
        self.setCentralWidget(central)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())