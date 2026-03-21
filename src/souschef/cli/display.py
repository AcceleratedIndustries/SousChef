"""Display CLI commands."""
import json
from typing import Optional

import typer

from souschef.db.connection import get_db, get_db_path
from souschef.display.renderer import render_recipe, render_plan, render_grocery

app = typer.Typer(help="HTML display rendering commands.")


@app.command()
def render(
    recipe_id: Optional[int] = typer.Option(None, "--recipe-id", help="Recipe ID to render."),
    plan_id: Optional[int] = typer.Option(None, "--plan-id", help="Plan ID to render."),
    grocery_id: Optional[int] = typer.Option(None, "--grocery-id", help="Grocery list ID to render."),
):
    """Render a recipe, plan, or grocery list to HTML."""
    if recipe_id is None and plan_id is None and grocery_id is None:
        typer.echo(json.dumps({"error": "must provide --recipe-id, --plan-id, or --grocery-id"}))
        raise typer.Exit(code=1)

    db_path = get_db_path()
    output_dir = db_path.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    conn = get_db()
    try:
        if recipe_id is not None:
            path = render_recipe(conn, recipe_id, output_dir)
        elif plan_id is not None:
            path = render_plan(conn, plan_id, output_dir)
        else:
            path = render_grocery(conn, grocery_id, output_dir)
    finally:
        conn.close()

    typer.echo(json.dumps({"path": str(path), "status": "rendered"}))
