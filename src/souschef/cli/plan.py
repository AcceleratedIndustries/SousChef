"""Plan CLI commands."""
import json
from typing import Optional

import typer

from souschef.db.connection import get_db
from souschef.cli.utils import _maybe_log
from souschef.models.plan import (
    create_plan,
    get_plan,
    edit_plan,
    delete_plan,
    add_plan_item,
    remove_plan_item,
    get_plan_items,
    list_plans,
    suggest_recipes,
)

app = typer.Typer(help="Meal plan commands.")


@app.command()
def create(
    name: str = typer.Option(..., "--name", help="Plan name."),
    start: Optional[str] = typer.Option(None, "--start", help="Start date (YYYY-MM-DD)."),
    end: Optional[str] = typer.Option(None, "--end", help="End date (YYYY-MM-DD)."),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Create a new meal plan."""
    conn = get_db()
    try:
        plan_id = create_plan(conn, name, start_date=start, end_date=end)
        _maybe_log(conn, log_user_msg, log_assistant_msg, "create", "plan", plan_id)
    finally:
        conn.close()
    typer.echo(json.dumps({"id": plan_id, "status": "created"}))


@app.command()
def view(plan_id: int = typer.Argument(..., help="Plan ID.")):
    """View a meal plan and its items."""
    conn = get_db()
    try:
        plan = get_plan(conn, plan_id)
        if plan is None:
            typer.echo(json.dumps({"error": f"plan {plan_id} not found"}))
            raise typer.Exit(code=1)
        items = get_plan_items(conn, plan_id)
    finally:
        conn.close()
    result = dict(plan)
    result["items"] = items
    typer.echo(json.dumps(result, default=str))


@app.command()
def add(
    plan_id: int = typer.Argument(..., help="Plan ID."),
    recipe_id: int = typer.Argument(..., help="Recipe ID."),
    date: str = typer.Option(..., "--date", help="Date (YYYY-MM-DD)."),
    meal: str = typer.Option(..., "--meal", help="Meal category (e.g. dinner)."),
    servings: Optional[int] = typer.Option(None, "--servings", help="Servings override."),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Add a recipe to a meal plan."""
    conn = get_db()
    try:
        item_id = add_plan_item(conn, plan_id, recipe_id, date, meal, servings_override=servings)
        _maybe_log(conn, log_user_msg, log_assistant_msg, "add_item", "plan", plan_id)
    finally:
        conn.close()
    typer.echo(json.dumps({"item_id": item_id, "status": "added"}))


@app.command()
def remove(
    plan_id: int = typer.Argument(..., help="Plan ID."),
    item_id: int = typer.Argument(..., help="Item ID."),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Remove an item from a meal plan."""
    conn = get_db()
    try:
        deleted = remove_plan_item(conn, plan_id, item_id)
        _maybe_log(conn, log_user_msg, log_assistant_msg, "remove_item", "plan", plan_id)
    finally:
        conn.close()
    if not deleted:
        typer.echo(json.dumps({"error": f"item {item_id} not found in plan {plan_id}"}))
        raise typer.Exit(code=1)
    typer.echo(json.dumps({"item_id": item_id, "status": "removed"}))


@app.command()
def edit(
    plan_id: int = typer.Argument(..., help="Plan ID."),
    name: Optional[str] = typer.Option(None, "--name", help="New name."),
    start: Optional[str] = typer.Option(None, "--start", help="New start date."),
    end: Optional[str] = typer.Option(None, "--end", help="New end date."),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Edit a meal plan."""
    conn = get_db()
    try:
        edit_plan(conn, plan_id, name=name, start_date=start, end_date=end)
        _maybe_log(conn, log_user_msg, log_assistant_msg, "edit", "plan", plan_id)
    finally:
        conn.close()
    typer.echo(json.dumps({"id": plan_id, "status": "updated"}))


@app.command()
def delete(
    plan_id: int = typer.Argument(..., help="Plan ID."),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Delete a meal plan."""
    conn = get_db()
    try:
        _maybe_log(conn, log_user_msg, log_assistant_msg, "delete", "plan", plan_id)
        deleted = delete_plan(conn, plan_id)
    finally:
        conn.close()
    if not deleted:
        typer.echo(json.dumps({"error": f"plan {plan_id} not found"}))
        raise typer.Exit(code=1)
    typer.echo(json.dumps({"id": plan_id, "status": "deleted"}))


@app.command()
def suggest(
    limit: int = typer.Option(10, "--limit", help="Number of suggestions."),
):
    """Suggest recipes for planning."""
    conn = get_db()
    try:
        recipes = suggest_recipes(conn, limit=limit)
    finally:
        conn.close()
    typer.echo(json.dumps(recipes, default=str))


@app.command(name="list")
def list_cmd():
    """List all meal plans."""
    conn = get_db()
    try:
        plans = list_plans(conn)
    finally:
        conn.close()
    typer.echo(json.dumps(plans, default=str))
