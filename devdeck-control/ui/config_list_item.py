from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt


class ConfigListItem(QWidget):
    def __init__(self, name, on_delete):
        super().__init__()

        self.on_delete = on_delete

        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)

        self.label = QLabel(name)

        self.delete_btn = QPushButton("🗑")
        self.delete_btn.setFixedWidth(30)
        self.delete_btn.clicked.connect(self.on_delete)
        self.delete_btn.hide()

        layout.addWidget(self.label)
        layout.addWidget(self.delete_btn)

        self.setLayout(layout)

    def enterEvent(self, event):
        self.delete_btn.show()

    def leaveEvent(self, event):
        self.delete_btn.hide()

    def set_text(self, text):
        self.label.setText(text)