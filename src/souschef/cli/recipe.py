"""Recipe CLI commands."""
import json
from typing import List, Optional

import typer

from souschef.db.connection import get_db
from souschef.cli.utils import _maybe_log
from souschef.models.recipe import (
    add_recipe,
    get_recipe,
    edit_recipe,
    delete_recipe,
    list_recipes,
    search_recipes,
    rate_recipe,
    favorite_recipe,
)
from souschef.models.dietary import set_dietary, get_dietary
from souschef.models.history import record_change
from souschef.models.chat import log_chat

app = typer.Typer(help="Recipe management commands.")


@app.command()
def add(
    json_data: Optional[str] = typer.Option(None, "--json", help="Full recipe JSON object."),
    title: Optional[str] = typer.Option(None, "--title", help="Recipe title (convenience)."),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Add a new recipe."""
    if json_data:
        data = json.loads(json_data)
    elif title:
        data = {"title": title}
    else:
        typer.echo(json.dumps({"error": "must provide --json or --title"}))
        raise typer.Exit(code=1)

    conn = get_db()
    try:
        recipe_id = add_recipe(conn, data)
        _maybe_log(conn, log_user_msg, log_assistant_msg, "add", "recipe", recipe_id)
    finally:
        conn.close()
    typer.echo(json.dumps({"id": recipe_id, "status": "created"}))


@app.command()
def view(recipe_id: int = typer.Argument(..., help="Recipe ID.")):
    """View a recipe by ID."""
    conn = get_db()
    try:
        recipe = get_recipe(conn, recipe_id)
    finally:
        conn.close()
    if recipe is None:
        typer.echo(json.dumps({"error": f"recipe {recipe_id} not found"}))
        raise typer.Exit(code=1)
    typer.echo(json.dumps(recipe, default=str))


@app.command()
def edit(
    recipe_id: int = typer.Argument(..., help="Recipe ID."),
    json_data: str = typer.Option(..., "--json", help="JSON patch object."),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Edit a recipe with a merge-patch JSON object."""
    changes = json.loads(json_data)
    conn = get_db()
    try:
        old_recipe = get_recipe(conn, recipe_id)
        if old_recipe is None:
            typer.echo(json.dumps({"error": f"recipe {recipe_id} not found"}))
            raise typer.Exit(code=1)
        edit_recipe(conn, recipe_id, changes)
        record_change(conn, recipe_id, changes, old_recipe)
        _maybe_log(conn, log_user_msg, log_assistant_msg, "edit", "recipe", recipe_id)
    finally:
        conn.close()
    typer.echo(json.dumps({"id": recipe_id, "status": "updated"}))


@app.command(name="list")
def list_cmd(
    tag: Optional[str] = typer.Option(None, "--tag"),
    category: Optional[str] = typer.Option(None, "--category"),
    favorite: Optional[bool] = typer.Option(None, "--favorite/--no-favorite"),
    limit: int = typer.Option(50, "--limit"),
    offset: int = typer.Option(0, "--offset"),
    sort: str = typer.Option("date", "--sort"),
):
    """List recipes with optional filters."""
    conn = get_db()
    try:
        recipes = list_recipes(
            conn,
            tag=tag,
            category=category,
            favorite=favorite,
            limit=limit,
            offset=offset,
            sort=sort,
        )
    finally:
        conn.close()
    typer.echo(json.dumps(recipes, default=str))


@app.command()
def search(query: str = typer.Argument(..., help="Search query.")):
    """Search recipes by title, description, or ingredients."""
    conn = get_db()
    try:
        results = search_recipes(conn, query)
    finally:
        conn.close()
    typer.echo(json.dumps(results, default=str))


@app.command()
def delete(
    recipe_id: int = typer.Argument(..., help="Recipe ID."),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Delete a recipe by ID."""
    conn = get_db()
    try:
        _maybe_log(conn, log_user_msg, log_assistant_msg, "delete", "recipe", recipe_id)
        deleted = delete_recipe(conn, recipe_id)
    finally:
        conn.close()
    if not deleted:
        typer.echo(json.dumps({"error": f"recipe {recipe_id} not found"}))
        raise typer.Exit(code=1)
    typer.echo(json.dumps({"id": recipe_id, "status": "deleted"}))


@app.command()
def rate(
    recipe_id: int = typer.Argument(..., help="Recipe ID."),
    rating: int = typer.Option(..., "--rating", help="Rating (1-5)."),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Rate a recipe (1-5)."""
    conn = get_db()
    try:
        rate_recipe(conn, recipe_id, rating)
        _maybe_log(conn, log_user_msg, log_assistant_msg, "rate", "recipe", recipe_id)
    except ValueError as e:
        typer.echo(json.dumps({"error": str(e)}))
        raise typer.Exit(code=1)
    finally:
        conn.close()
    typer.echo(json.dumps({"id": recipe_id, "rating": rating}))


@app.command()
def favorite(
    recipe_id: int = typer.Argument(..., help="Recipe ID."),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Toggle favorite status for a recipe."""
    conn = get_db()
    try:
        recipe = get_recipe(conn, recipe_id)
        if recipe is None:
            typer.echo(json.dumps({"error": f"recipe {recipe_id} not found"}))
            raise typer.Exit(code=1)
        current = bool(recipe.get("is_favorite"))
        new_value = not current
        favorite_recipe(conn, recipe_id, new_value)
        _maybe_log(conn, log_user_msg, log_assistant_msg, "favorite", "recipe", recipe_id)
    finally:
        conn.close()
    typer.echo(json.dumps({"id": recipe_id, "is_favorite": new_value}))


@app.command(name="set-dietary")
def set_dietary_cmd(
    recipe_id: int = typer.Argument(..., help="Recipe ID."),
    flags: List[str] = typer.Argument(..., help="Dietary flags (e.g. vegan gluten-free)."),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Set dietary flags for a recipe."""
    conn = get_db()
    try:
        set_dietary(conn, recipe_id, flags)
        dietary = get_dietary(conn, recipe_id)
        _maybe_log(conn, log_user_msg, log_assistant_msg, "set_dietary", "recipe", recipe_id)
    finally:
        conn.close()
    typer.echo(json.dumps({"id": recipe_id, "dietary": dietary}))


@app.command(name="import-url")
def import_url(
    url: str = typer.Argument(..., help="URL to fetch and scrape."),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Import a recipe from a URL."""
    from souschef.db.connection import get_db_path
    from souschef.scraper.url import fetch_and_scrape

    db_path = get_db_path()
    images_dir = db_path.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    scraped = fetch_and_scrape(url, images_dir)

    recipe_data = {
        "title": scraped.get("title") or url,
        "source_url": scraped.get("source_url"),
        "source_type": "url",
        "instructions": scraped.get("instructions"),
        "ingredients": scraped.get("ingredients_raw"),
        "servings": scraped.get("servings"),
        "image_path": str(scraped["image_path"]) if scraped.get("image_path") else None,
    }
    recipe_data = {k: v for k, v in recipe_data.items() if v is not None}

    conn = get_db()
    try:
        recipe_id = add_recipe(conn, recipe_data)
        _maybe_log(conn, log_user_msg, log_assistant_msg, "import_url", "recipe", recipe_id)
    finally:
        conn.close()
    typer.echo(json.dumps({"id": recipe_id, "title": recipe_data["title"], "status": "imported"}))
