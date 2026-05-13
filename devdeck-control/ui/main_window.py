import json
from dataclasses import asdict

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget,
    QPushButton, QFileDialog, QListWidgetItem
)

from models.configuration import Configuration, ButtonConfig, EncoderConfig, NUM_BUTTONS, NUM_ENCODERS
from ui.config_form import ConfigForm
from ui.config_list_item import ConfigListItem
import db.database as db


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("DevDeck Config")
        self.resize(1100, 750)

        self.configs: list[Configuration] = []
        self.db_ids: list[int] = []

        db.init_db()

        layout = QHBoxLayout()

        # -------- LEFT PANEL
        left_layout = QVBoxLayout()

        top_bar = QHBoxLayout()
        btn_add = QPushButton("+")
        btn_add.clicked.connect(self.add_config)
        btn_save = QPushButton("Save JSON")
        btn_save.clicked.connect(self.export_json)
        btn_load = QPushButton("Load JSON")
        btn_load.clicked.connect(self.import_json)
        top_bar.addWidget(btn_add)
        top_bar.addWidget(btn_save)
        top_bar.addWidget(btn_load)

        self.list = QListWidget()
        self.list.currentRowChanged.connect(self.select)

        left_layout.addLayout(top_bar)
        left_layout.addWidget(self.list)

        # -------- RIGHT PANEL
        self.form = ConfigForm()
        self.form.save_btn.clicked.connect(self.autosave)
        self.form.changed.connect(self.autosave)
        self.form.set_enabled(False)

        layout.addLayout(left_layout, 1)
        layout.addWidget(self.form, 3)
        self.setLayout(layout)

        self._load_from_db()

    def _default_config(self, name: str) -> Configuration:
        return Configuration(
            name=name,
            buttons=[ButtonConfig() for _ in range(NUM_BUTTONS)],
            encoders=[EncoderConfig() for _ in range(NUM_ENCODERS)],
        )

    def _load_from_db(self):
        for row_id, cfg in db.load_all():
            self.configs.append(cfg)
            self.db_ids.append(row_id)
            self.add_list_item(cfg)

    def add_config(self):
        cfg = self._default_config("New Config")
        row_id = db.insert(cfg)
        self.configs.append(cfg)
        self.db_ids.append(row_id)
        self.add_list_item(cfg)
        self.list.setCurrentRow(len(self.configs) - 1)

    def add_list_item(self, cfg: Configuration):
        item = QListWidgetItem()
        widget = ConfigListItem(cfg.name, lambda: self.delete_item(item))
        item.setSizeHint(widget.sizeHint())
        self.list.addItem(item)
        self.list.setItemWidget(item, widget)

    def delete_item(self, item: QListWidgetItem):
        row = self.list.row(item)
        db.delete(self.db_ids[row])
        self.list.takeItem(row)
        self.configs.pop(row)
        self.db_ids.pop(row)

        if not self.configs:
            self.form.clear()
            self.form.set_enabled(False)
            return

        self.list.setCurrentRow(min(row, len(self.configs) - 1))

    def select(self, idx: int):
        if idx < 0 or idx >= len(self.configs):
            self.form.clear()
            self.form.set_enabled(False)
            return
        self.form.set_enabled(True)
        self.form.load(self.configs[idx])

    def autosave(self):
        idx = self.list.currentRow()
        if idx < 0:
            return
        self.form.save()
        db.update(self.db_ids[idx], self.configs[idx])
        widget = self.list.itemWidget(self.list.item(idx))
        if widget is not None:
            widget.set_text(self.configs[idx].name)  # type: ignore[attr-defined]

    def export_json(self):
        file, _ = QFileDialog.getSaveFileName(self, "Save JSON", "", "JSON (*.json)")
        if not file:
            return
        with open(file, "w") as f:
            json.dump([asdict(c) for c in self.configs], f, indent=4)

    def import_json(self):
        file, _ = QFileDialog.getOpenFileName(self, "Load JSON", "", "JSON (*.json)")
        if not file:
            return
        with open(file, "r") as f:
            data = json.load(f)

        new_configs = [Configuration(**c) for c in data]
        db.replace_all(new_configs)

        self.configs.clear()
        self.db_ids.clear()
        self.list.clear()
        self.form.clear()
        self.form.set_enabled(False)
        self._load_from_db()