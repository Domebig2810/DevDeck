import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QDoubleSpinBox, QFileDialog, QHBoxLayout,
    QScrollArea, QMessageBox, QRadioButton,
    QFrame, QTabWidget
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from models.configuration import Configuration, ButtonConfig, EncoderConfig, NUM_BUTTONS, NUM_ENCODERS
from utils.image_utils import convert_to_bmp_128x64
from utils.command_runner import run_command

# ──────────────────────────────────────────────────────────────────────────────
# ButtonCard
# ──────────────────────────────────────────────────────────────────────────────

class ButtonCard(QWidget):
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

        # ---- LEFT: badge + preview ----
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

        self.preview = QLabel("–")
        self.preview.setFixedSize(80, 40)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet(
            "border: 1px solid palette(mid); border-radius: 4px;"
            "background: palette(window); font-size: 12px; font-weight: bold;"
        )

        left.addWidget(badge, alignment=Qt.AlignmentFlag.AlignHCenter)
        left.addWidget(self.preview)

        # ---- RIGHT: fields ----
        right = QVBoxLayout()
        right.setSpacing(6)

        # Toggle
        toggle_row = QHBoxLayout()
        self.radio_label = QRadioButton("Label")
        self.radio_image = QRadioButton("Bild")
        self.radio_label.setChecked(True)
        self.radio_label.setStyleSheet("font-size: 12px;")
        self.radio_image.setStyleSheet("font-size: 12px;")
        self.radio_label.toggled.connect(self._on_mode_changed)
        toggle_row.addWidget(self.radio_label)
        toggle_row.addWidget(self.radio_image)
        toggle_row.addStretch()

        # Label row
        self.label_row = QWidget()
        lr = QHBoxLayout(self.label_row)
        lr.setContentsMargins(0, 0, 0, 0)
        lr.setSpacing(8)
        ll = QLabel("Label")
        ll.setFixedWidth(56)
        ll.setStyleSheet("font-size: 12px; color: palette(mid);")
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("Button label")
        self.label_edit.setFixedHeight(28)
        self.label_edit.textChanged.connect(self._on_label_changed)
        lr.addWidget(ll)
        lr.addWidget(self.label_edit)

        # Image row
        self.image_row = QWidget()
        ir = QHBoxLayout(self.image_row)
        ir.setContentsMargins(0, 0, 0, 0)
        ir.setSpacing(8)
        il = QLabel("Bild")
        il.setFixedWidth(56)
        il.setStyleSheet("font-size: 12px; color: palette(mid);")
        self.image_path_edit = QLineEdit()
        self.image_path_edit.setPlaceholderText("Kein Bild gewählt")
        self.image_path_edit.setFixedHeight(28)
        self.image_path_edit.setReadOnly(True)
        self.image_path_edit.setStyleSheet("color: palette(mid); font-style: italic;")
        self.import_btn = QPushButton("↑")
        self.import_btn.setFixedSize(28, 28)
        self.import_btn.setToolTip("Bild importieren")
        self.import_btn.clicked.connect(self._import_image)
        ir.addWidget(il)
        ir.addWidget(self.image_path_edit)
        ir.addWidget(self.import_btn)
        self.image_row.hide()

        # Command row
        cmd_row = QHBoxLayout()
        cmd_row.setSpacing(8)
        cl = QLabel("Command")
        cl.setFixedWidth(56)
        cl.setStyleSheet("font-size: 12px; color: palette(mid);")
        self.cmd_edit = QLineEdit()
        self.cmd_edit.setPlaceholderText("z.B.  firefox  |  open -a 'Chrome'")
        self.cmd_edit.setFixedHeight(28)
        self.cmd_edit.textChanged.connect(self._emit_changed)
        self.run_btn = QPushButton("▶ Run")
        self.run_btn.setFixedWidth(64)
        self.run_btn.setFixedHeight(28)
        self.run_btn.clicked.connect(self._test_command)
        cmd_row.addWidget(cl)
        cmd_row.addWidget(self.cmd_edit)
        cmd_row.addWidget(self.run_btn)

        right.addLayout(toggle_row)
        right.addWidget(self.label_row)
        right.addWidget(self.image_row)
        right.addLayout(cmd_row)

        outer.addLayout(left)
        outer.addLayout(right, 1)
        self.setLayout(outer)

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
            self.preview.setPixmap(QPixmap())
            self.preview.setText(self.label_edit.text().strip() or "–")
            self.preview.setStyleSheet(
                "border: 1px solid palette(mid); border-radius: 4px;"
                "background: palette(window); font-size: 12px; font-weight: bold;"
            )
        else:
            path = self.image_path_edit.text()
            if path and os.path.exists(path):
                pix = QPixmap(path).scaled(
                    80, 40,
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
            self, "Bild wählen", "", "Images (*.png *.jpg *.bmp)")
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
            QMessageBox.warning(self, "Kein Command",
                                f"Button {self.index + 1} hat keinen Command.")
            return
        success, message = run_command(cmd)
        self._flash_btn(self.run_btn, success)
        if not success:
            QMessageBox.critical(self, "Command fehlgeschlagen",
                                 f"Button {self.index + 1}:\n\n{message}")

    def _flash_btn(self, btn: QPushButton, success: bool):
        if success:
            btn.setStyleSheet("background:#2d7a2d;color:white;border:none;")
            btn.setText("✓ OK")
        else:
            btn.setStyleSheet("background:#8b2020;color:white;border:none;")
            btn.setText("✗ Fail")
        QTimer.singleShot(2500, lambda: self._reset_btn(btn))

    def _reset_btn(self, btn: QPushButton):
        btn.setStyleSheet("")
        btn.setText("▶ Run")

    def load(self, cfg: ButtonConfig):
        self._loading = True
        self.label_edit.setText(cfg.label)
        self.cmd_edit.setText(cfg.command)
        self.image_path_edit.setText(cfg.image)
        if cfg.display_mode == "image":
            self.radio_image.setChecked(True)
        else:
            self.radio_label.setChecked(True)
        self._on_mode_changed()
        self._reset_btn(self.run_btn)
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
        self._reset_btn(self.run_btn)
        self._loading = False


# ──────────────────────────────────────────────────────────────────────────────
# EncoderCard
# ──────────────────────────────────────────────────────────────────────────────

class EncoderCard(QWidget):
    changed = pyqtSignal()

    def __init__(self, index: int):
        super().__init__()
        self.index = index
        self._loading = False

        self.setObjectName("EncoderCard")
        self.setStyleSheet("""
            QWidget#EncoderCard {
                border: 1px solid palette(mid);
                border-radius: 8px;
                background: palette(base);
            }
        """)

        outer = QHBoxLayout()
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(14)

        # Badge
        badge = QLabel(str(index + 1))
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(22, 22)
        badge.setStyleSheet(
            "border-radius: 11px; background: palette(midlight);"
            "color: palette(text); font-size: 11px; font-weight: bold;"
        )

        # Fields
        right = QVBoxLayout()
        right.setSpacing(6)

        # Step row
        step_row = QHBoxLayout()
        step_row.setSpacing(8)
        sl = QLabel("Step")
        sl.setFixedWidth(72)
        sl.setStyleSheet("font-size: 12px; color: palette(mid);")
        self.step_spin = QDoubleSpinBox()
        self.step_spin.setRange(0.01, 999999)
        self.step_spin.setValue(1.0)
        self.step_spin.setFixedHeight(28)
        self.step_spin.setToolTip("Schrittgröße pro Encoder-Tick; {step} im Command")
        self.step_spin.valueChanged.connect(self._emit_changed)
        step_row.addWidget(sl)
        step_row.addWidget(self.step_spin)
        step_row.addStretch()

        # Clockwise row
        cw_row = QHBoxLayout()
        cw_row.setSpacing(8)
        cwl = QLabel("↻ Rechts")
        cwl.setFixedWidth(72)
        cwl.setStyleSheet("font-size: 12px; color: palette(mid);")
        self.cw_edit = QLineEdit()
        self.cw_edit.setPlaceholderText(
            "z.B.  osascript -e 'set volume output volume "
            "(output volume of (get volume settings) + {step})'"
        )
        self.cw_edit.setFixedHeight(28)
        self.cw_edit.textChanged.connect(self._emit_changed)
        self.cw_run_btn = QPushButton("▶ Run")
        self.cw_run_btn.setFixedWidth(64)
        self.cw_run_btn.setFixedHeight(28)
        self.cw_run_btn.clicked.connect(self._test_cw)
        cw_row.addWidget(cwl)
        cw_row.addWidget(self.cw_edit)
        cw_row.addWidget(self.cw_run_btn)

        # Counter-clockwise row
        ccw_row = QHBoxLayout()
        ccw_row.setSpacing(8)
        ccwl = QLabel("↺ Links")
        ccwl.setFixedWidth(72)
        ccwl.setStyleSheet("font-size: 12px; color: palette(mid);")
        self.ccw_edit = QLineEdit()
        self.ccw_edit.setPlaceholderText(
            "z.B.  osascript -e 'set volume output volume "
            "(output volume of (get volume settings) - {step})'"
        )
        self.ccw_edit.setFixedHeight(28)
        self.ccw_edit.textChanged.connect(self._emit_changed)
        self.ccw_run_btn = QPushButton("▶ Run")
        self.ccw_run_btn.setFixedWidth(64)
        self.ccw_run_btn.setFixedHeight(28)
        self.ccw_run_btn.clicked.connect(self._test_ccw)
        ccw_row.addWidget(ccwl)
        ccw_row.addWidget(self.ccw_edit)
        ccw_row.addWidget(self.ccw_run_btn)

        # Click row
        click_row = QHBoxLayout()
        click_row.setSpacing(8)
        clickl = QLabel("⏎ Klick")
        clickl.setFixedWidth(72)
        clickl.setStyleSheet("font-size: 12px; color: palette(mid);")
        self.click_edit = QLineEdit()
        self.click_edit.setPlaceholderText(
            "z.B.  osascript -e 'tell app \"Music\" to playpause'"
        )
        self.click_edit.setFixedHeight(28)
        self.click_edit.textChanged.connect(self._emit_changed)
        self.click_run_btn = QPushButton("▶ Run")
        self.click_run_btn.setFixedWidth(64)
        self.click_run_btn.setFixedHeight(28)
        self.click_run_btn.clicked.connect(self._test_click)
        click_row.addWidget(clickl)
        click_row.addWidget(self.click_edit)
        click_row.addWidget(self.click_run_btn)

        right.addLayout(step_row)
        right.addLayout(cw_row)
        right.addLayout(ccw_row)
        right.addLayout(click_row)

        outer.addWidget(badge, alignment=Qt.AlignmentFlag.AlignTop)
        outer.addLayout(right, 1)
        self.setLayout(outer)

    def _emit_changed(self):
        if not self._loading:
            self.changed.emit()

    def _test_cw(self):
        self._test(self.cw_edit, self.cw_run_btn, "↻ Rechts")

    def _test_ccw(self):
        self._test(self.ccw_edit, self.ccw_run_btn, "↺ Links")

    def _test_click(self):
        self._test(self.click_edit, self.click_run_btn, "Klick", use_step=False)

    def _test(self, edit: QLineEdit, btn: QPushButton, label: str, use_step: bool = True):
        cmd = edit.text().strip()
        if not cmd:
            QMessageBox.warning(self, "Kein Command",
                                f"Encoder {self.index + 1} ({label}) hat keinen Command.")
            return
        step = self.step_spin.value() if use_step else None
        success, message = run_command(cmd, step=step)
        self._flash_btn(btn, success)
        if not success:
            QMessageBox.critical(self, "Command fehlgeschlagen",
                                 f"Encoder {self.index + 1} ({label}):\n\n{message}")

    def _flash_btn(self, btn: QPushButton, success: bool):
        if success:
            btn.setStyleSheet("background:#2d7a2d;color:white;border:none;")
            btn.setText("✓ OK")
        else:
            btn.setStyleSheet("background:#8b2020;color:white;border:none;")
            btn.setText("✗ Fail")
        QTimer.singleShot(2500, lambda: self._reset_btn(btn))

    def _reset_btn(self, btn: QPushButton):
        btn.setStyleSheet("")
        btn.setText("▶ Run")

    def load(self, cfg: EncoderConfig):
        self._loading = True
        self.step_spin.setValue(cfg.step)
        self.cw_edit.setText(cfg.clockwise_command)
        self.ccw_edit.setText(cfg.counter_command)
        self.click_edit.setText(cfg.click_command)
        for btn in (self.cw_run_btn, self.ccw_run_btn, self.click_run_btn):
            self._reset_btn(btn)
        self._loading = False

    def get_config(self) -> EncoderConfig:
        return EncoderConfig(
            step=self.step_spin.value(),
            clockwise_command=self.cw_edit.text(),
            counter_command=self.ccw_edit.text(),
            click_command=self.click_edit.text(),
        )

    def clear(self):
        self._loading = True
        self.step_spin.setValue(1.0)
        self.cw_edit.clear()
        self.ccw_edit.clear()
        self.click_edit.clear()
        for btn in (self.cw_run_btn, self.ccw_run_btn, self.click_run_btn):
            self._reset_btn(btn)
        self._loading = False


# ──────────────────────────────────────────────────────────────────────────────
# ConfigForm
# ──────────────────────────────────────────────────────────────────────────────

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

        # Tab widget
        tabs = QTabWidget()

        # ---- Tab 1: Buttons ----
        btn_scroll = QScrollArea()
        btn_scroll.setWidgetResizable(True)
        btn_scroll.setFrameShape(QFrame.Shape.NoFrame)
        btn_content = QWidget()
        btn_layout = QVBoxLayout(btn_content)
        btn_layout.setSpacing(8)
        btn_layout.setContentsMargins(4, 8, 4, 4)

        self.button_cards: list[ButtonCard] = []
        for i in range(NUM_BUTTONS):
            card = ButtonCard(i)
            card.changed.connect(self._on_changed)
            self.button_cards.append(card)
            btn_layout.addWidget(card)
        btn_layout.addStretch()

        btn_scroll.setWidget(btn_content)
        tabs.addTab(btn_scroll, "Buttons")

        # ---- Tab 2: Encoders ----
        enc_scroll = QScrollArea()
        enc_scroll.setWidgetResizable(True)
        enc_scroll.setFrameShape(QFrame.Shape.NoFrame)
        enc_content = QWidget()
        enc_layout = QVBoxLayout(enc_content)
        enc_layout.setSpacing(8)
        enc_layout.setContentsMargins(4, 8, 4, 4)

        self.encoder_cards: list[EncoderCard] = []
        for i in range(NUM_ENCODERS):
            card = EncoderCard(i)
            card.changed.connect(self._on_changed)
            self.encoder_cards.append(card)
            enc_layout.addWidget(card)
        enc_layout.addStretch()

        enc_scroll.setWidget(enc_content)
        tabs.addTab(enc_scroll, "Encoder")

        main_layout.addLayout(top_bar)
        main_layout.addWidget(tabs)
        self.setLayout(main_layout)

    def _on_changed(self):
        if not self._loading and self.current_config:
            self.changed.emit()

    def load(self, config: Configuration):
        self._loading = True
        self.current_config = config
        self.name_edit.setText(config.name)
        for i in range(NUM_BUTTONS):
            self.button_cards[i].load(config.buttons[i])
        for i in range(NUM_ENCODERS):
            self.encoder_cards[i].load(config.encoders[i])
        self._loading = False

    def save(self):
        if not self.current_config:
            return
        cfg = self.current_config
        cfg.name = self.name_edit.text()
        cfg.buttons = [card.get_config() for card in self.button_cards]
        cfg.encoders = [card.get_config() for card in self.encoder_cards]

    def clear(self):
        self._loading = True
        self.current_config = None
        self.name_edit.clear()
        for card in self.button_cards:
            card.clear()
        for card in self.encoder_cards:
            card.clear()
        self._loading = False

    def set_enabled(self, enabled: bool):
        self.setEnabled(enabled)