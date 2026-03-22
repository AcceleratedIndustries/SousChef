"""Update management CLI commands."""

import json

import typer

from souschef.update import get_repo_root, check_for_updates, apply_update

app = typer.Typer(help="Check for and apply updates.")


@app.command()
def check():
    """Check if a SousChef update is available."""
    repo_root = get_repo_root()
    if repo_root is None:
        typer.echo(json.dumps({"status": "error", "error": "Not a git repository"}))
        raise typer.Exit(code=1)

    result = check_for_updates(repo_root)
    typer.echo(json.dumps(result, default=str))
    if result["status"] == "error":
        raise typer.Exit(code=1)


@app.command()
def apply():
    """Pull latest updates and reinstall SousChef."""
    repo_root = get_repo_root()
    if repo_root is None:
        typer.echo(json.dumps({"status": "error", "error": "Not a git repository"}))
        raise typer.Exit(code=1)

    result = apply_update(repo_root)
    typer.echo(json.dumps(result, default=str))
    if result["status"] == "error":
        raise typer.Exit(code=1)
