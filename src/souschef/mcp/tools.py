"""MCP tool registrations.

Each tool opens a DB connection, calls the underlying model function, and
returns a JSON-serializable result.

Mutating tools require both `user_intent` (the user's request in their words)
and `assistant_summary` (Claude's terse description of what was done). Both are
written to chat_log within the same DB transaction as the mutation, preserving
the atomic logging contract from the original design and ensuring
`recipe_history.chat_log_id` foreign keys are populated for full traceability.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from souschef.db.connection import get_db, get_db_path
from souschef.models import dietary as dietary_model
from souschef.models import grocery as grocery_model
from souschef.models import plan as plan_model
from souschef.models import recipe as recipe_model
from souschef.models import tag as tag_model
from souschef.models.chat import log_chat, search_chat
from souschef.models.history import record_change


def _log(
    conn,
    user_intent: str,
    assistant_summary: str,
    action: str,
    entity_type: str,
    entity_id: int | None,
) -> int:
    return log_chat(
        conn,
        user_message=user_intent,
        assistant_response=assistant_summary,
        action_type=action,
        entity_type=entity_type,
        entity_id=entity_id,
    )


def _output_dir() -> Path:
    out = get_db_path().parent / "output"
    out.mkdir(parents=True, exist_ok=True)
    return out


def register(mcp: FastMCP) -> None:
    # ------------------------------------------------------------------
    # Recipes
    # ------------------------------------------------------------------

    @mcp.tool()
    def recipe_add(
        recipe: dict[str, Any],
        user_intent: str,
        assistant_summary: str,
    ) -> dict:
        """Add a new recipe.

        `recipe` is the full recipe object: title (required), description,
        prep_time_minutes, cook_time_minutes, servings, ingredients
        (list of {name, quantity, unit}), instructions (ordered list of
        strings), notes, source_type ("manual" | "url"), source_url.
        """
        conn = get_db()
        try:
            recipe_id = recipe_model.add_recipe(conn, recipe)
            _log(conn, user_intent, assistant_summary, "add", "recipe", recipe_id)
        finally:
            conn.close()
        return {"id": recipe_id, "status": "created"}

    @mcp.tool()
    def recipe_view(recipe_id: int) -> dict:
        """View a recipe by ID."""
        conn = get_db()
        try:
            row = recipe_model.get_recipe(conn, recipe_id)
        finally:
            conn.close()
        if row is None:
            return {"error": f"recipe {recipe_id} not found"}
        return row

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
            return recipe_model.list_recipes(
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

    @mcp.tool()
    def recipe_search(query: str, limit: int = 100) -> list[dict]:
        """Search recipes by title, description, or ingredients (AND across
        whitespace-separated terms)."""
        conn = get_db()
        try:
            return recipe_model.search_recipes(conn, query, limit=limit)
        finally:
            conn.close()

    @mcp.tool()
    def recipe_edit(
        recipe_id: int,
        changes: dict[str, Any],
        user_intent: str,
        assistant_summary: str,
    ) -> dict:
        """Merge-patch update: only the fields in `changes` are updated.
        Records field-level history linked to this conversation."""
        conn = get_db()
        try:
            old = recipe_model.get_recipe(conn, recipe_id)
            if old is None:
                return {"error": f"recipe {recipe_id} not found"}
            recipe_model.edit_recipe(conn, recipe_id, changes)
            chat_id = _log(
                conn, user_intent, assistant_summary, "edit", "recipe", recipe_id
            )
            record_change(conn, recipe_id, changes, old, chat_log_id=chat_id)
        finally:
            conn.close()
        return {"id": recipe_id, "status": "updated"}

    @mcp.tool()
    def recipe_delete(
        recipe_id: int,
        user_intent: str,
        assistant_summary: str,
    ) -> dict:
        """Delete a recipe by ID."""
        conn = get_db()
        try:
            _log(
                conn, user_intent, assistant_summary, "delete", "recipe", recipe_id
            )
            deleted = recipe_model.delete_recipe(conn, recipe_id)
        finally:
            conn.close()
        if not deleted:
            return {"error": f"recipe {recipe_id} not found"}
        return {"id": recipe_id, "status": "deleted"}

    @mcp.tool()
    def recipe_rate(
        recipe_id: int,
        rating: int,
        user_intent: str,
        assistant_summary: str,
    ) -> dict:
        """Rate a recipe 1-5."""
        conn = get_db()
        try:
            try:
                recipe_model.rate_recipe(conn, recipe_id, rating)
            except ValueError as e:
                return {"error": str(e)}
            _log(conn, user_intent, assistant_summary, "rate", "recipe", recipe_id)
        finally:
            conn.close()
        return {"id": recipe_id, "rating": rating}

    @mcp.tool()
    def recipe_favorite(
        recipe_id: int,
        user_intent: str,
        assistant_summary: str,
    ) -> dict:
        """Toggle the favorite flag on a recipe."""
        conn = get_db()
        try:
            row = recipe_model.get_recipe(conn, recipe_id)
            if row is None:
                return {"error": f"recipe {recipe_id} not found"}
            new_value = not bool(row.get("is_favorite"))
            recipe_model.favorite_recipe(conn, recipe_id, new_value)
            _log(
                conn, user_intent, assistant_summary, "favorite", "recipe", recipe_id
            )
        finally:
            conn.close()
        return {"id": recipe_id, "is_favorite": new_value}

    @mcp.tool()
    def recipe_set_dietary(
        recipe_id: int,
        flags: list[str],
        user_intent: str,
        assistant_summary: str,
    ) -> dict:
        """Replace the dietary flag set for a recipe.
        Common flags: vegan, vegetarian, gluten-free, dairy-free, nut-free,
        low-carb, keto, paleo."""
        conn = get_db()
        try:
            dietary_model.set_dietary(conn, recipe_id, flags)
            current = dietary_model.get_dietary(conn, recipe_id)
            _log(
                conn,
                user_intent,
                assistant_summary,
                "set_dietary",
                "recipe",
                recipe_id,
            )
        finally:
            conn.close()
        return {"id": recipe_id, "dietary": current}

    @mcp.tool()
    def recipe_import_url(
        url: str,
        user_intent: str,
        assistant_summary: str,
    ) -> dict:
        """Fetch a URL, scrape recipe schema/JSON-LD, download the hero
        image, and create a recipe with source_type="url"."""
        from souschef.scraper.url import fetch_and_scrape

        images_dir = get_db_path().parent / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        scraped = fetch_and_scrape(url, images_dir)
        data = {
            "title": scraped.get("title") or url,
            "source_url": scraped.get("source_url"),
            "source_type": "url",
            "instructions": scraped.get("instructions"),
            "ingredients": scraped.get("ingredients_raw"),
            "servings": scraped.get("servings"),
            "image_path": str(scraped["image_path"])
            if scraped.get("image_path")
            else None,
        }
        data = {k: v for k, v in data.items() if v is not None}

        conn = get_db()
        try:
            recipe_id = recipe_model.add_recipe(conn, data)
            _log(
                conn,
                user_intent,
                assistant_summary,
                "import_url",
                "recipe",
                recipe_id,
            )
        finally:
            conn.close()
        return {"id": recipe_id, "title": data["title"], "status": "imported"}

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------

    @mcp.tool()
    def tag_add(
        recipe_id: int,
        tags: list[str],
        user_intent: str,
        assistant_summary: str,
    ) -> dict:
        """Add tags to a recipe (lowercase, deduped, existing tags reused)."""
        conn = get_db()
        try:
            tag_model.add_tags(conn, recipe_id, tags)
            current = tag_model.get_tags_for_recipe(conn, recipe_id)
            _log(
                conn, user_intent, assistant_summary, "tag_add", "recipe", recipe_id
            )
        finally:
            conn.close()
        return {"recipe_id": recipe_id, "tags": current}

    @mcp.tool()
    def tag_remove(
        recipe_id: int,
        tag: str,
        user_intent: str,
        assistant_summary: str,
    ) -> dict:
        """Remove a single tag from a recipe."""
        conn = get_db()
        try:
            tag_model.remove_tag(conn, recipe_id, tag)
            current = tag_model.get_tags_for_recipe(conn, recipe_id)
            _log(
                conn,
                user_intent,
                assistant_summary,
                "tag_remove",
                "recipe",
                recipe_id,
            )
        finally:
            conn.close()
        return {"recipe_id": recipe_id, "tags": current}

    @mcp.tool()
    def tag_list() -> list[dict]:
        """List all tags with usage counts, ordered by count DESC."""
        conn = get_db()
        try:
            return tag_model.list_tags(conn)
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Meal plans
    # ------------------------------------------------------------------

    @mcp.tool()
    def plan_create(
        name: str,
        user_intent: str,
        assistant_summary: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict:
        """Create a meal plan. Dates are YYYY-MM-DD strings."""
        conn = get_db()
        try:
            plan_id = plan_model.create_plan(conn, name, start_date, end_date)
            _log(
                conn,
                user_intent,
                assistant_summary,
                "plan_create",
                "plan",
                plan_id,
            )
        finally:
            conn.close()
        return {"id": plan_id, "status": "created"}

    @mcp.tool()
    def plan_add(
        plan_id: int,
        recipe_id: int,
        date: str,
        meal_category: str,
        user_intent: str,
        assistant_summary: str,
        servings_override: int | None = None,
    ) -> dict:
        """Add a recipe to a meal plan on a specific date for a meal
        category (breakfast, lunch, dinner, snack, brunch, dessert, side,
        appetizer)."""
        conn = get_db()
        try:
            try:
                item_id = plan_model.add_plan_item(
                    conn,
                    plan_id,
                    recipe_id,
                    date,
                    meal_category,
                    servings_override=servings_override,
                )
            except ValueError as e:
                return {"error": str(e)}
            _log(
                conn,
                user_intent,
                assistant_summary,
                "plan_add",
                "plan",
                plan_id,
            )
        finally:
            conn.close()
        return {"id": item_id, "plan_id": plan_id, "status": "added"}

    @mcp.tool()
    def plan_view(plan_id: int) -> dict:
        """View a plan with all its items."""
        conn = get_db()
        try:
            plan = plan_model.get_plan(conn, plan_id)
            if plan is None:
                return {"error": f"plan {plan_id} not found"}
            items = plan_model.get_plan_items(conn, plan_id)
        finally:
            conn.close()
        return {"plan": plan, "items": items}

    @mcp.tool()
    def plan_suggest(limit: int = 10) -> list[dict]:
        """Suggest recipes for planning, prioritizing least-recently-planned
        and highest-rated."""
        conn = get_db()
        try:
            return plan_model.suggest_recipes(conn, limit=limit)
        finally:
            conn.close()

    @mcp.tool()
    def plan_list() -> list[dict]:
        """List all meal plans, newest first."""
        conn = get_db()
        try:
            return plan_model.list_plans(conn)
        finally:
            conn.close()

    @mcp.tool()
    def plan_edit(
        plan_id: int,
        user_intent: str,
        assistant_summary: str,
        name: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict:
        """Edit plan name and/or date range. Only non-null fields are updated."""
        conn = get_db()
        try:
            existing = plan_model.get_plan(conn, plan_id)
            if existing is None:
                return {"error": f"plan {plan_id} not found"}
            plan_model.edit_plan(
                conn, plan_id, name=name, start_date=start_date, end_date=end_date
            )
            _log(
                conn,
                user_intent,
                assistant_summary,
                "plan_edit",
                "plan",
                plan_id,
            )
        finally:
            conn.close()
        return {"id": plan_id, "status": "updated"}

    @mcp.tool()
    def plan_delete(
        plan_id: int,
        user_intent: str,
        assistant_summary: str,
    ) -> dict:
        """Delete a meal plan (cascades to items)."""
        conn = get_db()
        try:
            _log(
                conn,
                user_intent,
                assistant_summary,
                "plan_delete",
                "plan",
                plan_id,
            )
            deleted = plan_model.delete_plan(conn, plan_id)
        finally:
            conn.close()
        if not deleted:
            return {"error": f"plan {plan_id} not found"}
        return {"id": plan_id, "status": "deleted"}

    @mcp.tool()
    def plan_remove(
        plan_id: int,
        item_id: int,
        user_intent: str,
        assistant_summary: str,
    ) -> dict:
        """Remove a single item from a plan. Item IDs come from `plan_view`."""
        conn = get_db()
        try:
            removed = plan_model.remove_plan_item(conn, plan_id, item_id)
            if not removed:
                return {"error": f"item {item_id} not found in plan {plan_id}"}
            _log(
                conn,
                user_intent,
                assistant_summary,
                "plan_remove",
                "plan",
                plan_id,
            )
        finally:
            conn.close()
        return {"plan_id": plan_id, "item_id": item_id, "status": "removed"}

    # ------------------------------------------------------------------
    # Grocery
    # ------------------------------------------------------------------

    @mcp.tool()
    def grocery_generate(
        plan_id: int,
        user_intent: str,
        assistant_summary: str,
        servings_multiplier: float = 1.0,
    ) -> dict:
        """Generate a grocery list from a meal plan.
        Normalizes units, combines compatible quantities, infers store sections."""
        conn = get_db()
        try:
            try:
                list_id = grocery_model.generate_from_plan(
                    conn, plan_id, servings_multiplier=servings_multiplier
                )
            except ValueError as e:
                return {"error": str(e)}
            _log(
                conn,
                user_intent,
                assistant_summary,
                "grocery_generate",
                "grocery_list",
                list_id,
            )
        finally:
            conn.close()
        return {"id": list_id, "plan_id": plan_id, "status": "generated"}

    @mcp.tool()
    def grocery_create(
        name: str,
        user_intent: str,
        assistant_summary: str,
    ) -> dict:
        """Create an empty standalone grocery list."""
        conn = get_db()
        try:
            list_id = grocery_model.create_list(conn, name)
            _log(
                conn,
                user_intent,
                assistant_summary,
                "grocery_create",
                "grocery_list",
                list_id,
            )
        finally:
            conn.close()
        return {"id": list_id, "status": "created"}

    @mcp.tool()
    def grocery_add_item(
        list_id: int,
        name: str,
        user_intent: str,
        assistant_summary: str,
        quantity: float | None = None,
        unit: str | None = None,
        section: str | None = None,
    ) -> dict:
        """Add an item to a grocery list. `section` is auto-inferred if not given."""
        conn = get_db()
        try:
            item_id = grocery_model.add_item(
                conn,
                list_id,
                name,
                quantity=quantity,
                unit=unit,
                store_section=section,
            )
            _log(
                conn,
                user_intent,
                assistant_summary,
                "grocery_add_item",
                "grocery_list",
                list_id,
            )
        finally:
            conn.close()
        return {"id": item_id, "list_id": list_id, "status": "added"}

    @mcp.tool()
    def grocery_view(list_id: int) -> dict:
        """View a grocery list with all items, grouped by store section."""
        conn = get_db()
        try:
            gl = grocery_model.get_list(conn, list_id)
            if gl is None:
                return {"error": f"grocery list {list_id} not found"}
            items = grocery_model.get_items(conn, list_id)
        finally:
            conn.close()
        return {"list": gl, "items": items}

    @mcp.tool()
    def grocery_check(
        list_id: int,
        item_id: int,
        user_intent: str,
        assistant_summary: str,
        checked: bool = True,
    ) -> dict:
        """Check or uncheck a grocery item."""
        conn = get_db()
        try:
            grocery_model.check_item(conn, list_id, item_id, checked=checked)
            _log(
                conn,
                user_intent,
                assistant_summary,
                "grocery_check",
                "grocery_list",
                list_id,
            )
        finally:
            conn.close()
        return {"list_id": list_id, "item_id": item_id, "checked": checked}

    @mcp.tool()
    def grocery_export(list_id: int) -> dict:
        """Return the grocery list as plain-text markdown, grouped by section."""
        conn = get_db()
        try:
            text = grocery_model.export_list(conn, list_id)
        finally:
            conn.close()
        if text is None:
            return {"error": f"grocery list {list_id} not found"}
        return {"id": list_id, "text": text}

    @mcp.tool()
    def grocery_list() -> list[dict]:
        """List all grocery lists, newest first."""
        conn = get_db()
        try:
            return grocery_model.list_lists(conn)
        finally:
            conn.close()

    @mcp.tool()
    def grocery_delete(
        list_id: int,
        user_intent: str,
        assistant_summary: str,
    ) -> dict:
        """Delete a grocery list (cascades to items)."""
        conn = get_db()
        try:
            _log(
                conn,
                user_intent,
                assistant_summary,
                "grocery_delete",
                "grocery_list",
                list_id,
            )
            deleted = grocery_model.delete_list(conn, list_id)
        finally:
            conn.close()
        if not deleted:
            return {"error": f"grocery list {list_id} not found"}
        return {"id": list_id, "status": "deleted"}

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    @mcp.tool()
    def display_render(
        recipe_id: int | None = None,
        plan_id: int | None = None,
        grocery_id: int | None = None,
    ) -> dict:
        """Render a recipe, plan, or grocery list as HTML. Returns the
        output file path. Provide exactly one of the three IDs."""
        from souschef.display.renderer import (
            render_recipe,
            render_plan,
            render_grocery,
        )

        provided = sum(
            1 for x in (recipe_id, plan_id, grocery_id) if x is not None
        )
        if provided != 1:
            return {"error": "provide exactly one of recipe_id, plan_id, grocery_id"}

        out = _output_dir()
        conn = get_db()
        try:
            if recipe_id is not None:
                path = render_recipe(conn, recipe_id, out)
            elif plan_id is not None:
                path = render_plan(conn, plan_id, out)
            else:
                path = render_grocery(conn, grocery_id, out)
        finally:
            conn.close()
        return {"path": str(path), "status": "rendered"}

    # ------------------------------------------------------------------
    # Chat / history
    # ------------------------------------------------------------------

    @mcp.tool()
    def chat_log_browse(
        user_intent: str,
        assistant_summary: str,
        action: str = "browse",
        entity_type: str | None = None,
        entity_id: int | None = None,
    ) -> dict:
        """Log a non-mutating interaction (browsing, Q&A, suggestions).
        For mutating tools, logging is automatic — don't call this."""
        conn = get_db()
        try:
            log_id = _log(
                conn, user_intent, assistant_summary, action, entity_type, entity_id
            )
        finally:
            conn.close()
        return {"id": log_id, "status": "logged"}

    @mcp.tool()
    def chat_search(query: str) -> list[dict]:
        """Full-text search across chat history."""
        conn = get_db()
        try:
            return search_chat(conn, query)
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Admin
    # ------------------------------------------------------------------

    @mcp.tool()
    def db_stats() -> dict:
        """Counts of rows in the main tables."""
        conn = get_db()
        try:
            counts = {}
            for table in [
                "recipes",
                "tags",
                "meal_plans",
                "grocery_lists",
                "chat_log",
            ]:
                row = conn.execute(
                    f"SELECT COUNT(*) AS c FROM {table}"
                ).fetchone()
                counts[table] = row["c"] if hasattr(row, "keys") else row[0]
        finally:
            conn.close()
        return counts
