import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QGridLayout, QGroupBox, QDoubleSpinBox, QFileDialog, QHBoxLayout, QScrollArea
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, pyqtSignal

from models.configuration import Configuration
from utils.image_utils import convert_to_bmp_128x64


class ConfigForm(QWidget):
    changed = pyqtSignal()  # fires on every user edit

    def __init__(self):
        super().__init__()

        self.current_config = None
        self._loading = False  # guard: suppress signals while load() fills fields

        main_layout = QVBoxLayout()

        # ---------------- TOP BAR
        top_bar = QHBoxLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Configuration Name")
        self.name_edit.textChanged.connect(self._on_changed)

        self.save_btn = QPushButton("Save")

        top_bar.addWidget(self.name_edit)
        top_bar.addWidget(self.save_btn)

        # ---------------- SCROLL AREA
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        layout = QVBoxLayout()

        # Buttons
        self.button_edits = []
        btn_group = QGroupBox("Buttons")
        btn_layout = QGridLayout()

        for i in range(6):
            e = QLineEdit()
            e.textChanged.connect(self._on_changed)
            self.button_edits.append(e)
            btn_layout.addWidget(QLabel(f"{i+1}"), i, 0)
            btn_layout.addWidget(e, i, 1)

        btn_group.setLayout(btn_layout)

        # Images
        self.image_labels = []
        img_group = QGroupBox("Displays (128x64)")
        img_layout = QGridLayout()

        for i in range(6):
            label = QLabel("No Image")
            label.setFixedSize(128, 64)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("border:1px solid gray")

            btn = QPushButton("Import")
            btn.clicked.connect(lambda _, idx=i: self.import_image(idx))

            self.image_labels.append(label)

            img_layout.addWidget(label, i, 0)
            img_layout.addWidget(btn, i, 1)

        img_group.setLayout(img_layout)

        # Pots
        self.pot_edits = []
        pot_group = QGroupBox("Potentiometer")
        pot_layout = QGridLayout()

        for i in range(6):
            spin = QDoubleSpinBox()
            spin.setRange(-9999, 9999)
            spin.valueChanged.connect(self._on_changed)
            self.pot_edits.append(spin)

            pot_layout.addWidget(QLabel(f"{i+1}"), i, 0)
            pot_layout.addWidget(spin, i, 1)

        pot_group.setLayout(pot_layout)

        layout.addWidget(btn_group)
        layout.addWidget(img_group)
        layout.addWidget(pot_group)
        layout.addStretch()

        content.setLayout(layout)
        scroll.setWidget(content)

        # Assemble
        main_layout.addLayout(top_bar)
        main_layout.addWidget(scroll)

        self.setLayout(main_layout)

    # -------- internal

    def _on_changed(self):
        if not self._loading and self.current_config:
            self.changed.emit()

    # -------- public API

    def load(self, config: Configuration):
        self._loading = True
        self.current_config = config

        self.name_edit.setText(config.name)

        for i in range(6):
            self.button_edits[i].setText(config.buttons[i])
            self.pot_edits[i].setValue(config.pots[i])

            if config.images[i] and os.path.exists(config.images[i]):
                pix = QPixmap(config.images[i]).scaled(128, 64)
                self.image_labels[i].setPixmap(pix)
            else:
                self.image_labels[i].setText("No Image")

        self._loading = False

    def save(self):
        if not self.current_config:
            return

        cfg = self.current_config
        cfg.name = self.name_edit.text()
        cfg.buttons = [e.text() for e in self.button_edits]
        cfg.pots = [p.value() for p in self.pot_edits]

    def import_image(self, index):
        file, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.bmp)")
        if not file:
            return

        os.makedirs("images", exist_ok=True)
        out = f"images/img_{index}_{id(self)}.bmp"

        convert_to_bmp_128x64(file, out)

        self.current_config.images[index] = out
        pix = QPixmap(out).scaled(128, 64)
        self.image_labels[index].setPixmap(pix)

        self._on_changed()  # image import also triggers autosave

    def clear(self):
        self._loading = True
        self.current_config = None

        self.name_edit.clear()

        for i in range(6):
            self.button_edits[i].clear()
            self.pot_edits[i].setValue(0.0)
            self.image_labels[i].setText("No Image")
            self.image_labels[i].setPixmap(QPixmap())

        self._loading = False

    def set_enabled(self, enabled: bool):
        self.setEnabled(enabled)