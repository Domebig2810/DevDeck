from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton


class CreateTab(QWidget):
    def __init__(self, on_create_callback):
        super().__init__()

        self.on_create_callback = on_create_callback

        layout = QVBoxLayout()

        self.name_input = QLineEdit()

        btn_create = QPushButton("Create")
        btn_create.clicked.connect(self.create)

        layout.addWidget(QLabel("Configuration Name"))
        layout.addWidget(self.name_input)
        layout.addWidget(btn_create)
        layout.addStretch()

        self.setLayout(layout)

    def create(self):
        name = self.name_input.text().strip()
        if name:
            self.on_create_callback(name)
            self.name_input.clear()