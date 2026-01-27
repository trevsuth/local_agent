# mcp/server/db.py
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional


def get_db_path(explicit: Optional[str] = None) -> Path:
    """
    Resolve the SQLite DB path.

    Precedence:
      1) explicit argument
      2) MCP_DB_PATH env var
      3) default: data/mcp_demo.sqlite (repo-relative)
    """
    if explicit:
        return Path(explicit)

    env = os.environ.get("MCP_DB_PATH")
    if env:
        return Path(env)

    return Path("data") / "mcp_demo.sqlite"


def connect(db_path: Path) -> sqlite3.Connection:
    """
    Open a SQLite connection with sensible defaults for this project.
    """
    # Ensure parent directory exists (if creating the DB elsewhere)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Safety + consistency
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")  # ms

    return conn


@contextmanager
def db_session(db_path: Path) -> Iterator[sqlite3.Connection]:
    """
    Context manager for a DB session.
    Keeps commit/rollback rules explicit for later write tools.
    """
    conn = connect(db_path)
    try:
        yield conn
    finally:
        conn.close()
