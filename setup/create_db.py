# setup/create_db.py
"""
Create or update the SQLite schema by executing setup/schema.sql.

Usage:
  python setup/create_db.py --db data/mcp_demo.sqlite --schema setup/schema.sql
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import typer

app = typer.Typer(help="Create or update the SQLite database schema.")


@app.command()
def create(
    db: Path = typer.Option(
        ...,
        "--db",
        help="Path to SQLite database file (e.g. data/mcp_demo.sqlite)",
        exists=False,
        file_okay=True,
        dir_okay=False,
        writable=True,
    ),
    schema: Path = typer.Option(
        ...,
        "--schema",
        help="Path to schema.sql (e.g. setup/schema.sql)",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
):
    """
    Execute the schema SQL against the target SQLite database.
    """
    typer.echo(f"📄 Reading schema from {schema}")
    ddl = schema.read_text(encoding="utf-8")

    typer.echo(f"🗄️  Creating/updating database at {db}")
    conn = sqlite3.connect(db)
    try:
        conn.executescript(ddl)
        conn.commit()
    finally:
        conn.close()

    typer.secho(
        "✅ Database schema created/updated successfully.", fg=typer.colors.GREEN
    )


def main():
    app()


if __name__ == "__main__":
    main()
