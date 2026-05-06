import json
from dataclasses import asdict

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget,
    QPushButton, QFileDialog, QListWidgetItem
)

from models.configuration import Configuration
from ui.config_form import ConfigForm
from ui.config_list_item import ConfigListItem
import db.database as db


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Config Tool")
        self.resize(1100, 700)

        self.configs = []   # list[Configuration]
        self.db_ids = []    # list[int]  – parallel to self.configs

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

        # load persisted data
        self._load_from_db()

    # -------- DB

    def _load_from_db(self):
        for row_id, cfg in db.load_all():
            self.configs.append(cfg)
            self.db_ids.append(row_id)
            self.add_list_item(cfg)

    # -------- LOGIC

    def add_config(self):
        cfg = Configuration(
            name="New Config",
            buttons=[""] * 6,
            images=[""] * 6,
            pots=[0.0] * 6
        )

        row_id = db.insert(cfg)

        self.configs.append(cfg)
        self.db_ids.append(row_id)
        self.add_list_item(cfg)

        self.list.setCurrentRow(len(self.configs) - 1)

    def add_list_item(self, cfg):
        item = QListWidgetItem()

        widget = ConfigListItem(cfg.name, lambda: self.delete_item(item))
        item.setSizeHint(widget.sizeHint())

        self.list.addItem(item)
        self.list.setItemWidget(item, widget)

    def delete_item(self, item):
        row = self.list.row(item)

        db.delete(self.db_ids[row])

        self.list.takeItem(row)
        self.configs.pop(row)
        self.db_ids.pop(row)

        if not self.configs:
            self.form.clear()
            self.form.set_enabled(False)
            return

        new_row = min(row, len(self.configs) - 1)
        self.list.setCurrentRow(new_row)

    def select(self, idx):
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

        item = self.list.item(idx)
        widget = self.list.itemWidget(item)
        widget.set_text(self.configs[idx].name)

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

        # reload from DB to get fresh IDs
        self.configs.clear()
        self.db_ids.clear()
        self.list.clear()
        self.form.clear()
        self.form.set_enabled(False)

        self._load_from_db()