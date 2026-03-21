"""Grocery CLI commands."""
import json
from typing import Optional

import typer

from souschef.db.connection import get_db
from souschef.cli.utils import _maybe_log
from souschef.models.grocery import (
    create_list,
    get_list,
    delete_list,
    list_lists,
    add_item,
    check_item,
    get_items,
    export_list,
    generate_from_plan,
)

app = typer.Typer(help="Grocery list commands.")


@app.command()
def create(
    name: str = typer.Option(..., "--name", help="List name."),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Create a standalone grocery list."""
    conn = get_db()
    try:
        list_id = create_list(conn, name)
        _maybe_log(conn, log_user_msg, log_assistant_msg, "create", "grocery_list", list_id)
    finally:
        conn.close()
    typer.echo(json.dumps({"id": list_id, "status": "created"}))


@app.command()
def generate(
    plan_id: int = typer.Argument(..., help="Plan ID."),
    servings_multiplier: float = typer.Option(1.0, "--servings-multiplier", help="Multiplier for servings."),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Generate a grocery list from a meal plan."""
    conn = get_db()
    try:
        list_id = generate_from_plan(conn, plan_id, servings_multiplier=servings_multiplier)
        items = get_items(conn, list_id)
        _maybe_log(conn, log_user_msg, log_assistant_msg, "generate", "grocery_list", list_id)
    finally:
        conn.close()
    typer.echo(json.dumps({"id": list_id, "item_count": len(items), "status": "generated"}))


@app.command()
def view(list_id: int = typer.Argument(..., help="List ID.")):
    """View a grocery list and its items."""
    conn = get_db()
    try:
        grocery_list = get_list(conn, list_id)
        if grocery_list is None:
            typer.echo(json.dumps({"error": f"grocery list {list_id} not found"}))
            raise typer.Exit(code=1)
        items = get_items(conn, list_id)
    finally:
        conn.close()
    result = dict(grocery_list)
    result["items"] = items
    typer.echo(json.dumps(result, default=str))


@app.command(name="add-item")
def add_item_cmd(
    list_id: int = typer.Argument(..., help="List ID."),
    name: str = typer.Option(..., "--name", help="Item name."),
    quantity: Optional[float] = typer.Option(None, "--quantity", help="Quantity."),
    unit: Optional[str] = typer.Option(None, "--unit", help="Unit."),
    section: Optional[str] = typer.Option(None, "--section", help="Store section."),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Add an item to a grocery list."""
    conn = get_db()
    try:
        item_id = add_item(conn, list_id, name, quantity=quantity, unit=unit, store_section=section)
        _maybe_log(conn, log_user_msg, log_assistant_msg, "add_item", "grocery_list", list_id)
    finally:
        conn.close()
    typer.echo(json.dumps({"item_id": item_id, "status": "added"}))


@app.command()
def check(
    list_id: int = typer.Argument(..., help="List ID."),
    item_id: int = typer.Argument(..., help="Item ID."),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Check off an item on a grocery list."""
    conn = get_db()
    try:
        check_item(conn, list_id, item_id)
        _maybe_log(conn, log_user_msg, log_assistant_msg, "check_item", "grocery_list", list_id)
    finally:
        conn.close()
    typer.echo(json.dumps({"item_id": item_id, "status": "checked"}))


@app.command()
def delete(
    list_id: int = typer.Argument(..., help="List ID."),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Delete a grocery list."""
    conn = get_db()
    try:
        _maybe_log(conn, log_user_msg, log_assistant_msg, "delete", "grocery_list", list_id)
        deleted = delete_list(conn, list_id)
    finally:
        conn.close()
    if not deleted:
        typer.echo(json.dumps({"error": f"grocery list {list_id} not found"}))
        raise typer.Exit(code=1)
    typer.echo(json.dumps({"id": list_id, "status": "deleted"}))


@app.command(name="list")
def list_cmd():
    """List all grocery lists."""
    conn = get_db()
    try:
        lists = list_lists(conn)
    finally:
        conn.close()
    typer.echo(json.dumps(lists, default=str))


@app.command()
def export(list_id: int = typer.Argument(..., help="List ID.")):
    """Export a grocery list as plain text."""
    conn = get_db()
    try:
        text = export_list(conn, list_id)
    finally:
        conn.close()
    if text is None:
        typer.echo(f"Error: grocery list {list_id} not found")
        raise typer.Exit(code=1)
    typer.echo(text)
