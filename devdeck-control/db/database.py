import sqlite3
import json
from pathlib import Path
from models.configuration import Configuration

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
                images  TEXT    NOT NULL,
                pots    TEXT    NOT NULL
            )
        """)


def load_all() -> list[tuple[int, Configuration]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM configurations ORDER BY id").fetchall()
    return [
        (row["id"], Configuration(
            name=row["name"],
            buttons=json.loads(row["buttons"]),
            images=json.loads(row["images"]),
            pots=json.loads(row["pots"]),
        ))
        for row in rows
    ]


def insert(cfg: Configuration) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO configurations (name, buttons, images, pots) VALUES (?, ?, ?, ?)",
            (_s(cfg.name), json.dumps(cfg.buttons), json.dumps(cfg.images), json.dumps(cfg.pots))
        )
        return cur.lastrowid


def update(row_id: int, cfg: Configuration):
    with _connect() as conn:
        conn.execute(
            "UPDATE configurations SET name=?, buttons=?, images=?, pots=? WHERE id=?",
            (_s(cfg.name), json.dumps(cfg.buttons), json.dumps(cfg.images), json.dumps(cfg.pots), row_id)
        )


def delete(row_id: int):
    with _connect() as conn:
        conn.execute("DELETE FROM configurations WHERE id=?", (row_id,))


def replace_all(configs: list[Configuration]):
    """Used when loading a JSON file – clears DB and re-inserts everything."""
    with _connect() as conn:
        conn.execute("DELETE FROM configurations")
        for cfg in configs:
            conn.execute(
                "INSERT INTO configurations (name, buttons, images, pots) VALUES (?, ?, ?, ?)",
                (_s(cfg.name), json.dumps(cfg.buttons), json.dumps(cfg.images), json.dumps(cfg.pots))
            )


def _s(value):
    return value if value is not None else ""