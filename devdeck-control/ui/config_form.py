import os

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from models.configuration import ButtonConfig, Configuration
from utils.command_runner import run_command
from utils.image_utils import convert_to_bmp_128x64

NUM_BUTTONS = 6


class ButtonCard(QWidget):
    """One card representing a single button slot."""

    changed = pyqtSignal()

    def __init__(self, index: int):
        super().__init__()
        self.index = index
        self._loading = False

        self.setObjectName("ButtonCard")
        self.setStyleSheet("""
            QWidget#ButtonCard {
                border: 1px solid palette(mid);
                border-radius: 8px;
                background: palette(base);
            }
        """)

        outer = QHBoxLayout()
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(14)

        # ---- LEFT: index badge + preview ----
        left = QVBoxLayout()
        left.setSpacing(6)
        left.setAlignment(Qt.AlignmentFlag.AlignTop)

        badge = QLabel(str(index + 1))
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(22, 22)
        badge.setStyleSheet(
            "border-radius: 11px; background: palette(midlight);"
            "color: palette(text); font-size: 11px; font-weight: bold;"
        )

        self.preview = QLabel()
        self.preview.setFixedSize(80, 40)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet(
            "border: 1px solid palette(mid); border-radius: 4px;"
            "background: palette(window); font-size: 12px;"
        )
        self.preview.setText("–")

        left.addWidget(badge, alignment=Qt.AlignmentFlag.AlignHCenter)
        left.addWidget(self.preview)

        # ---- RIGHT: fields ----
        right = QVBoxLayout()
        right.setSpacing(6)

        # Toggle row
        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(0)
        self.radio_label = QRadioButton("Label")
        self.radio_image = QRadioButton("Bild")
        self.radio_label.setChecked(True)
        self.radio_label.setStyleSheet("font-size: 12px;")
        self.radio_image.setStyleSheet("font-size: 12px;")
        self.radio_label.toggled.connect(self._on_mode_changed)
        toggle_row.addWidget(self.radio_label)
        toggle_row.addWidget(self.radio_image)
        toggle_row.addStretch()

        # Label row (shown in label mode)
        self.label_row = QWidget()
        label_row_layout = QHBoxLayout(self.label_row)
        label_row_layout.setContentsMargins(0, 0, 0, 0)
        label_row_layout.setSpacing(8)
        lbl = QLabel("Label")
        lbl.setFixedWidth(56)
        lbl.setStyleSheet("font-size: 12px; color: palette(mid);")
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("Button label")
        self.label_edit.setFixedHeight(28)
        self.label_edit.textChanged.connect(self._on_label_changed)
        label_row_layout.addWidget(lbl)
        label_row_layout.addWidget(self.label_edit)

        # Image row (shown in image mode)
        self.image_row = QWidget()
        image_row_layout = QHBoxLayout(self.image_row)
        image_row_layout.setContentsMargins(0, 0, 0, 0)
        image_row_layout.setSpacing(8)
        img_lbl = QLabel("Bild")
        img_lbl.setFixedWidth(56)
        img_lbl.setStyleSheet("font-size: 12px; color: palette(mid);")
        self.image_path_edit = QLineEdit()
        self.image_path_edit.setPlaceholderText("Kein Bild gewählt")
        self.image_path_edit.setFixedHeight(28)
        self.image_path_edit.setReadOnly(True)
        self.image_path_edit.setStyleSheet("color: palette(mid); font-style: italic;")
        self.import_btn = QPushButton("↑")
        self.import_btn.setFixedSize(28, 28)
        self.import_btn.setToolTip("Bild importieren")
        self.import_btn.clicked.connect(self._import_image)
        image_row_layout.addWidget(img_lbl)
        image_row_layout.addWidget(self.image_path_edit)
        image_row_layout.addWidget(self.import_btn)
        self.image_row.hide()

        # Command row
        cmd_row = QHBoxLayout()
        cmd_row.setSpacing(8)
        cmd_lbl = QLabel("Command")
        cmd_lbl.setFixedWidth(56)
        cmd_lbl.setStyleSheet("font-size: 12px; color: palette(mid);")
        self.cmd_edit = QLineEdit()
        self.cmd_edit.setPlaceholderText(
            "z.B. firefox  |  notepad  |  open -a 'Chrome'"
        )
        self.cmd_edit.setFixedHeight(28)
        self.cmd_edit.textChanged.connect(self._emit_changed)
        self.run_btn = QPushButton("▶ Run")
        self.run_btn.setFixedWidth(64)
        self.run_btn.setFixedHeight(28)
        self.run_btn.setToolTip("Command testen")
        self.run_btn.clicked.connect(self._test_command)
        cmd_row.addWidget(cmd_lbl)
        cmd_row.addWidget(self.cmd_edit)
        cmd_row.addWidget(self.run_btn)

        right.addLayout(toggle_row)
        right.addWidget(self.label_row)
        right.addWidget(self.image_row)
        right.addLayout(cmd_row)

        outer.addLayout(left)
        outer.addLayout(right, 1)
        self.setLayout(outer)

    # ---- internal

    def _on_mode_changed(self):
        label_mode = self.radio_label.isChecked()
        self.label_row.setVisible(label_mode)
        self.image_row.setVisible(not label_mode)
        self._refresh_preview()
        if not self._loading:
            self.changed.emit()

    def _on_label_changed(self):
        self._refresh_preview()
        self._emit_changed()

    def _emit_changed(self):
        if not self._loading:
            self.changed.emit()

    def _refresh_preview(self):
        if self.radio_label.isChecked():
            text = self.label_edit.text().strip() or "–"
            self.preview.setPixmap(QPixmap())
            self.preview.setText(text)
            self.preview.setStyleSheet(
                "border: 1px solid palette(mid); border-radius: 4px;"
                "background: palette(window); font-size: 12px; font-weight: bold;"
            )
        else:
            path = self.image_path_edit.text()
            if path and os.path.exists(path):
                pix = QPixmap(path).scaled(
                    80,
                    40,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.preview.setPixmap(pix)
                self.preview.setText("")
            else:
                self.preview.setPixmap(QPixmap())
                self.preview.setText("kein Bild")
            self.preview.setStyleSheet(
                "border: 1px solid palette(mid); border-radius: 4px;"
                "background: #111; font-size: 10px; color: #888;"
            )

    def _import_image(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Bild wählen", "", "Images (*.png *.jpg *.bmp)"
        )
        if not file:
            return
        os.makedirs("images", exist_ok=True)
        out = f"images/btn_{self.index}_{id(self)}.bmp"
        convert_to_bmp_128x64(file, out)
        self.image_path_edit.setText(out)
        self._refresh_preview()
        self._emit_changed()

    def _test_command(self):
        cmd = self.cmd_edit.text().strip()
        if not cmd:
            QMessageBox.warning(
                self, "Kein Command", f"Button {self.index + 1} hat keinen Command."
            )
            return
        success, message = run_command(cmd)
        if success:
            self.run_btn.setStyleSheet(
                "background: #2d7a2d; color: white; border: none;"
            )
            self.run_btn.setText("✓ OK")
        else:
            self.run_btn.setStyleSheet(
                "background: #8b2020; color: white; border: none;"
            )
            self.run_btn.setText("✗ Fail")
            QMessageBox.critical(
                self, "Command fehlgeschlagen", f"Button {self.index + 1}:\n\n{message}"
            )
        QTimer.singleShot(2500, self._reset_run_btn)

    def _reset_run_btn(self):
        self.run_btn.setStyleSheet("")
        self.run_btn.setText("▶ Run")

    # ---- public API

    def load(self, cfg: ButtonConfig):
        self._loading = True
        self.label_edit.setText(cfg.label)
        self.cmd_edit.setText(cfg.command)
        self.image_path_edit.setText(cfg.image)
        if cfg.display_mode == "image":
            self.radio_image.setChecked(True)
        else:
            self.radio_label.setChecked(True)
        self._on_mode_changed()  # sync visibility + preview
        self._reset_run_btn()
        self._loading = False

    def get_config(self) -> ButtonConfig:
        return ButtonConfig(
            label=self.label_edit.text(),
            command=self.cmd_edit.text(),
            image=self.image_path_edit.text(),
            display_mode="image" if self.radio_image.isChecked() else "label",
        )

    def clear(self):
        self._loading = True
        self.label_edit.clear()
        self.cmd_edit.clear()
        self.image_path_edit.clear()
        self.radio_label.setChecked(True)
        self._on_mode_changed()
        self._reset_run_btn()
        self._loading = False


class ConfigForm(QWidget):
    changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current_config = None
        self._loading = False

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Top bar
        top_bar = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Konfigurationsname")
        self.name_edit.textChanged.connect(self._on_changed)
        self.save_btn = QPushButton("Speichern")
        top_bar.addWidget(self.name_edit)
        top_bar.addWidget(self.save_btn)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(8)
        content_layout.setContentsMargins(4, 4, 4, 4)

        # Button cards
        btn_group = QGroupBox("Buttons")
        btn_group_layout = QVBoxLayout(btn_group)
        btn_group_layout.setSpacing(8)

        self.button_cards: list[ButtonCard] = []
        for i in range(NUM_BUTTONS):
            card = ButtonCard(i)
            card.changed.connect(self._on_changed)
            self.button_cards.append(card)
            btn_group_layout.addWidget(card)

        # Pots
        pot_group = QGroupBox("Potentiometer")
        pot_layout = QGridLayout(pot_group)
        self.pot_edits: list[QDoubleSpinBox] = []
        for i in range(NUM_BUTTONS):
            spin = QDoubleSpinBox()
            spin.setRange(-9999, 9999)
            spin.valueChanged.connect(self._on_changed)
            self.pot_edits.append(spin)
            pot_layout.addWidget(QLabel(str(i + 1)), i, 0)
            pot_layout.addWidget(spin, i, 1)

        content_layout.addWidget(btn_group)
        content_layout.addWidget(pot_group)
        content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addLayout(top_bar)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    # ---- internal

    def _on_changed(self):
        if not self._loading and self.current_config:
            self.changed.emit()

    # ---- public API

    def load(self, config: Configuration):
        self._loading = True
        self.current_config = config
        self.name_edit.setText(config.name)
        for i in range(NUM_BUTTONS):
            self.button_cards[i].load(config.buttons[i])
            self.pot_edits[i].setValue(config.pots[i])
        self._loading = False

    def save(self):
        if not self.current_config:
            return
        cfg = self.current_config
        cfg.name = self.name_edit.text()
        cfg.buttons = [card.get_config() for card in self.button_cards]
        cfg.pots = [p.value() for p in self.pot_edits]

    def clear(self):
        self._loading = True
        self.current_config = None
        self.name_edit.clear()
        for card in self.button_cards:
            card.clear()
        for spin in self.pot_edits:
            spin.setValue(0.0)
        self._loading = False

    def set_enabled(self, enabled: bool):
        self.setEnabled(enabled)
