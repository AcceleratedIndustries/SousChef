"""Tag CLI commands."""
import json
from typing import List, Optional

import typer

from souschef.db.connection import get_db
from souschef.cli.utils import _maybe_log
from souschef.models.tag import add_tags, remove_tag, list_tags

app = typer.Typer(help="Tag management commands.")


@app.command()
def add(
    recipe_id: int = typer.Argument(..., help="Recipe ID."),
    tags: List[str] = typer.Argument(..., help="Tag names to add."),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Add tags to a recipe."""
    conn = get_db()
    try:
        add_tags(conn, recipe_id, tags)
        _maybe_log(conn, log_user_msg, log_assistant_msg, "add_tags", "recipe", recipe_id)
    finally:
        conn.close()
    normalized = [t.strip().lower() for t in tags if t.strip()]
    typer.echo(json.dumps({"recipe_id": recipe_id, "added": normalized}))


@app.command()
def remove(
    recipe_id: int = typer.Argument(..., help="Recipe ID."),
    tag: str = typer.Argument(..., help="Tag name to remove."),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Remove a tag from a recipe."""
    conn = get_db()
    try:
        remove_tag(conn, recipe_id, tag)
        _maybe_log(conn, log_user_msg, log_assistant_msg, "remove_tag", "recipe", recipe_id)
    finally:
        conn.close()
    typer.echo(json.dumps({"recipe_id": recipe_id, "removed": tag.strip().lower()}))


@app.command(name="list")
def list_cmd():
    """List all tags with usage counts."""
    conn = get_db()
    try:
        tags = list_tags(conn)
    finally:
        conn.close()
    typer.echo(json.dumps(tags))
