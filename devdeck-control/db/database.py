import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import List, Tuple

from models.configuration import ButtonConfig, Configuration, PotConfig

DB_PATH = Path("configs.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS configurations (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT    NOT NULL,
                buttons TEXT    NOT NULL,
                pots    TEXT    NOT NULL
            )
        """)
        # Migrate old schema that had an `images` column
        cols = [
            r[1] for r in conn.execute("PRAGMA table_info(configurations)").fetchall()
        ]
        if "images" in cols:
            conn.execute("ALTER TABLE configurations DROP COLUMN images")


def _buttons_to_json(buttons: List[ButtonConfig]) -> str:
    return json.dumps([asdict(b) for b in buttons])


def _pots_to_json(pots: List[PotConfig]) -> str:
    return json.dumps([asdict(p) for p in pots])


def _cfg_from_row(row) -> Tuple[int, Configuration]:
    return row["id"], Configuration(
        name=row["name"],
        buttons=json.loads(row["buttons"]),
        pots=json.loads(row["pots"]),
    )


def load_all() -> List[Tuple[int, Configuration]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM configurations ORDER BY id").fetchall()
    return [_cfg_from_row(r) for r in rows]


def insert(cfg: Configuration) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO configurations (name, buttons, pots) VALUES (?, ?, ?)",
            (_s(cfg.name), _buttons_to_json(cfg.buttons), _pots_to_json(cfg.pots)),
        )
        assert cur.lastrowid is not None
        return cur.lastrowid


def update(row_id: int, cfg: Configuration):
    with _connect() as conn:
        conn.execute(
            "UPDATE configurations SET name=?, buttons=?, pots=? WHERE id=?",
            (
                _s(cfg.name),
                _buttons_to_json(cfg.buttons),
                _pots_to_json(cfg.pots),
                row_id,
            ),
        )


def delete(row_id: int):
    with _connect() as conn:
        conn.execute("DELETE FROM configurations WHERE id=?", (row_id,))


def replace_all(configs: List[Configuration]):
    with _connect() as conn:
        conn.execute("DELETE FROM configurations")
        for cfg in configs:
            conn.execute(
                "INSERT INTO configurations (name, buttons, pots) VALUES (?, ?, ?)",
                (_s(cfg.name), _buttons_to_json(cfg.buttons), _pots_to_json(cfg.pots)),
            )


def _s(value):
    return value if value is not None else ""
