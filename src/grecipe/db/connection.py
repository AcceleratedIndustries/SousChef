"""Database connection management."""

import os
import sqlite3
from pathlib import Path

_DEFAULT_DB_DIR = Path.home() / ".grecipe"
_DB_NAME = "grecipe.db"


def get_db_path(db_dir: Path | None = None) -> Path:
    """Return the path to the database file."""
    if db_dir is None:
        env_dir = os.environ.get("GRECIPE_DB_DIR")
        directory = Path(env_dir) if env_dir else _DEFAULT_DB_DIR
    else:
        directory = db_dir
    directory.mkdir(parents=True, exist_ok=True)
    return directory / _DB_NAME


def get_db(db_path: Path | None = None) -> sqlite3.Connection:
    """Return a connection to the database with WAL mode and FK enforcement."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
