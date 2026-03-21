"""Tag CLI commands."""
import json
from typing import List, Optional

import typer

from grecipe.db.connection import get_db
from grecipe.models.tag import add_tags, remove_tag, list_tags
from grecipe.models.chat import log_chat

app = typer.Typer(help="Tag management commands.")


def _maybe_log(conn, user_msg, assistant_msg, action_type, entity_type, entity_id=None):
    """Log a chat entry if messages are provided."""
    if user_msg is not None or assistant_msg is not None:
        log_chat(
            conn,
            user_message=user_msg,
            assistant_response=assistant_msg,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
        )


@app.command()
def add(
    recipe_id: int = typer.Argument(..., help="Recipe ID."),
    tags: List[str] = typer.Argument(..., help="Tag names to add."),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Add tags to a recipe."""
    conn = get_db()
    add_tags(conn, recipe_id, tags)
    _maybe_log(conn, log_user_msg, log_assistant_msg, "add_tags", "recipe", recipe_id)
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
    remove_tag(conn, recipe_id, tag)
    _maybe_log(conn, log_user_msg, log_assistant_msg, "remove_tag", "recipe", recipe_id)
    conn.close()
    typer.echo(json.dumps({"recipe_id": recipe_id, "removed": tag.strip().lower()}))


@app.command(name="list")
def list_cmd():
    """List all tags with usage counts."""
    conn = get_db()
    tags = list_tags(conn)
    conn.close()
    typer.echo(json.dumps(tags))
