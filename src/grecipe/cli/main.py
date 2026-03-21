"""grecipe CLI entry point."""

import typer

app = typer.Typer(name="grecipe", help="Recipe management for Claude Cowork.")


def register_subcommands():
    from grecipe.cli.db_cmd import app as db_app
    from grecipe.cli.recipe import app as recipe_app
    from grecipe.cli.tag import app as tag_app
    app.add_typer(db_app, name="db")
    app.add_typer(recipe_app, name="recipe")
    app.add_typer(tag_app, name="tag")


register_subcommands()

if __name__ == "__main__":
    app()
