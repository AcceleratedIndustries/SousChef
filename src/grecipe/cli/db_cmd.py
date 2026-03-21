"""Database management commands."""

import json
import typer
from grecipe.db.connection import get_db, get_db_path
from grecipe.db.schema import init_db
from grecipe.db.seed import seed_meal_categories

app = typer.Typer(help="Database management.")


@app.command()
def init():
    """Initialize the database (create tables, seed data)."""
    db_path = get_db_path()
    conn = get_db(db_path)
    try:
        init_db(conn)
        seed_meal_categories(conn)
    finally:
        conn.close()
    typer.echo(json.dumps({"status": "ok", "db_path": str(db_path)}))


@app.command()
def stats():
    """Show database statistics."""
    conn = get_db()
    try:
        counts = {}
        for table in ["recipes", "tags", "meal_plans", "grocery_lists", "chat_log"]:
            row = conn.execute(f"SELECT COUNT(*) as c FROM {table}").fetchone()
            counts[table] = row["c"]
    finally:
        conn.close()
    typer.echo(json.dumps(counts))
