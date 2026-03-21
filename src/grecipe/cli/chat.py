"""Chat CLI commands."""
import json
from typing import Optional

import typer

from grecipe.db.connection import get_db
from grecipe.models.chat import log_chat, search_chat

app = typer.Typer(help="Chat log commands.")


@app.command()
def log(
    action: str = typer.Option(..., "--action", help="Action type."),
    entity_type: Optional[str] = typer.Option(None, "--entity-type", help="Entity type."),
    entity_id: Optional[int] = typer.Option(None, "--entity-id", help="Entity ID."),
    user_message: Optional[str] = typer.Option(None, "--user-message", help="User message."),
    assistant_response: Optional[str] = typer.Option(None, "--assistant-response", help="Assistant response."),
):
    """Log a chat interaction."""
    conn = get_db()
    try:
        log_id = log_chat(
            conn,
            user_message=user_message,
            assistant_response=assistant_response,
            action_type=action,
            entity_type=entity_type,
            entity_id=entity_id,
        )
    finally:
        conn.close()
    typer.echo(json.dumps({"id": log_id, "status": "logged"}))


@app.command()
def search(query: str = typer.Argument(..., help="Search query.")):
    """Search chat logs by full-text query."""
    conn = get_db()
    try:
        results = search_chat(conn, query)
    finally:
        conn.close()
    typer.echo(json.dumps(results, default=str))
