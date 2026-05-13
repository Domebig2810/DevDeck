import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import List, Tuple

from models.configuration import ButtonConfig, Configuration, EncoderConfig

DB_PATH = Path("configs.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        cols = [
            r[1] for r in conn.execute("PRAGMA table_info(configurations)").fetchall()
        ]

        if "pots" in cols and "encoders" not in cols:
            # Migrate: rebuild table replacing pots with encoders
            # 1. Read existing data
            rows = conn.execute(
                "SELECT id, name, buttons, pots FROM configurations"
            ).fetchall()

            # 2. Drop old table
            conn.execute("DROP TABLE configurations")

            # 3. Create new table
            conn.execute("""
                CREATE TABLE configurations (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    name     TEXT    NOT NULL,
                    buttons  TEXT    NOT NULL,
                    encoders TEXT    NOT NULL
                )
            """)

            # 4. Re-insert rows, converting pots → default EncoderConfigs
            for row in rows:
                old_pots = json.loads(row["pots"])
                new_encoders = [asdict(EncoderConfig()) for _ in old_pots]
                conn.execute(
                    "INSERT INTO configurations (id, name, buttons, encoders) VALUES (?, ?, ?, ?)",
                    (row["id"], row["name"], row["buttons"], json.dumps(new_encoders)),
                )
        else:
            # Fresh install
            conn.execute("""
                CREATE TABLE IF NOT EXISTS configurations (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    name     TEXT    NOT NULL,
                    buttons  TEXT    NOT NULL,
                    encoders TEXT    NOT NULL
                )
            """)

            # Drop legacy images column if present
            cols = [
                r[1]
                for r in conn.execute("PRAGMA table_info(configurations)").fetchall()
            ]
            if "images" in cols:
                conn.execute("ALTER TABLE configurations DROP COLUMN images")


def _buttons_to_json(buttons: List[ButtonConfig]) -> str:
    return json.dumps([asdict(b) for b in buttons])


def _encoders_to_json(encoders: List[EncoderConfig]) -> str:
    return json.dumps([asdict(e) for e in encoders])


def _cfg_from_row(row) -> Tuple[int, Configuration]:
    return row["id"], Configuration(
        name=row["name"],
        buttons=json.loads(row["buttons"]),
        encoders=json.loads(row["encoders"]),
    )


def load_all() -> List[Tuple[int, Configuration]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM configurations ORDER BY id").fetchall()
    return [_cfg_from_row(r) for r in rows]


def insert(cfg: Configuration) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO configurations (name, buttons, encoders) VALUES (?, ?, ?)",
            (
                _s(cfg.name),
                _buttons_to_json(cfg.buttons),
                _encoders_to_json(cfg.encoders),
            ),
        )
        assert cur.lastrowid is not None
        return cur.lastrowid


def update(row_id: int, cfg: Configuration):
    with _connect() as conn:
        conn.execute(
            "UPDATE configurations SET name=?, buttons=?, encoders=? WHERE id=?",
            (
                _s(cfg.name),
                _buttons_to_json(cfg.buttons),
                _encoders_to_json(cfg.encoders),
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
                "INSERT INTO configurations (name, buttons, encoders) VALUES (?, ?, ?)",
                (
                    _s(cfg.name),
                    _buttons_to_json(cfg.buttons),
                    _encoders_to_json(cfg.encoders),
                ),
            )


def _s(value):
    return value if value is not None else ""
