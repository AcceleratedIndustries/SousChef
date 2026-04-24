"""MCP tool registrations.

Each tool opens a DB connection, calls the underlying model function, and
returns a JSON-serializable result. Mutating tools auto-log to chat_log via
`_log` and accept an optional `user_intent` for color.

This file currently registers a representative subset (recipe_add, recipe_view,
recipe_list) so the shape can be reviewed before the remaining ~25 tools are
wired in.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from souschef.db.connection import get_db
from souschef.models.chat import log_chat
from souschef.models.recipe import (
    add_recipe,
    get_recipe,
    list_recipes,
)


def _log(
    conn,
    action: str,
    entity_type: str,
    entity_id: int | None,
    user_intent: str | None,
) -> None:
    log_chat(
        conn,
        user_message=user_intent,
        assistant_response=None,
        action_type=action,
        entity_type=entity_type,
        entity_id=entity_id,
    )


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def recipe_add(
        recipe: dict[str, Any],
        user_intent: str | None = None,
    ) -> dict:
        """Add a new recipe.

        `recipe` is a full recipe object: title (required), description,
        prep_time_minutes, cook_time_minutes, servings, ingredients
        (list of {name, quantity, unit}), instructions (ordered list of
        strings), notes, source_type ("manual" | "url").
        """
        conn = get_db()
        try:
            recipe_id = add_recipe(conn, recipe)
            _log(conn, "add", "recipe", recipe_id, user_intent)
        finally:
            conn.close()
        return {"id": recipe_id, "status": "created"}

    @mcp.tool()
    def recipe_view(recipe_id: int) -> dict:
        """View a recipe by ID."""
        conn = get_db()
        try:
            result = get_recipe(conn, recipe_id)
        finally:
            conn.close()
        if result is None:
            return {"error": f"recipe {recipe_id} not found"}
        return result

    @mcp.tool()
    def recipe_list(
        tag: str | None = None,
        category: str | None = None,
        favorite: bool | None = None,
        limit: int = 50,
        offset: int = 0,
        sort: str = "date",
    ) -> list[dict]:
        """List recipes. Filters: tag, category, favorite.
        Sort: "date" | "rating" | "title"."""
        conn = get_db()
        try:
            return list_recipes(
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

    # TODO: remaining tools follow the same shape —
    # recipe_search, recipe_edit, recipe_delete, recipe_rate,
    # recipe_favorite, recipe_set_dietary, recipe_import_url,
    # tag_*, plan_*, grocery_*, display_render, chat_search, db_stats.
