"""grecipe CLI entry point."""

import typer

app = typer.Typer(name="grecipe", help="Recipe management for Claude Cowork.")


def register_subcommands():
    from grecipe.cli.db_cmd import app as db_app
    app.add_typer(db_app, name="db")


register_subcommands()

if __name__ == "__main__":
    app()
