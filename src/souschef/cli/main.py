"""souschef CLI entry point."""

import typer

app = typer.Typer(name="souschef", help="Recipe management for Claude Cowork.")


def register_subcommands():
    from souschef.cli.db_cmd import app as db_app
    from souschef.cli.recipe import app as recipe_app
    from souschef.cli.tag import app as tag_app
    from souschef.cli.plan import app as plan_app
    from souschef.cli.grocery import app as grocery_app
    from souschef.cli.chat import app as chat_app
    from souschef.cli.display import app as display_app
    app.add_typer(db_app, name="db")
    app.add_typer(recipe_app, name="recipe")
    app.add_typer(tag_app, name="tag")
    app.add_typer(plan_app, name="plan")
    app.add_typer(grocery_app, name="grocery")
    app.add_typer(chat_app, name="chat")
    app.add_typer(display_app, name="display")


register_subcommands()

if __name__ == "__main__":
    app()
