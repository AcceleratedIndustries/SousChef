---
name: souschef
description: Use when the user wants to manage recipes, plan meals, or generate grocery lists. Triggers include "save this recipe", "what can I make for dinner", "plan next week's meals", "make a shopping list from the plan", "import the recipe at <url>", and any reference to the user's saved recipes, meal plans, or grocery lists.
---

# SousChef

Manage the user's recipe collection, meal plans, and grocery lists. Data lives in a local SQLite database; all operations go through the SousChef MCP tools.

## Tool surface

- **Recipes** — `recipe_add`, `recipe_view`, `recipe_list`, `recipe_search`, `recipe_edit`, `recipe_delete`, `recipe_rate`, `recipe_favorite`, `recipe_set_dietary`, `recipe_import_url`
- **Tags** — `tag_add`, `tag_remove`, `tag_list`
- **Meal plans** — `plan_create`, `plan_add`, `plan_view`, `plan_suggest`, `plan_list`, `plan_edit`, `plan_delete`, `plan_remove`
- **Groceries** — `grocery_generate`, `grocery_create`, `grocery_add_item`, `grocery_view`, `grocery_check`, `grocery_export`, `grocery_list`, `grocery_delete`
- **Display** — `display_render` (renders recipe / plan / grocery list as HTML, returns a file path)
- **History** — `chat_search`
- **Admin** — `db_stats`

Parameters and return shapes are in each tool's schema — consult those rather than guessing.

## Parse recipes, don't paste them

When the user describes a recipe in plain text, extract structure before calling `recipe_add`:
- `ingredients` as `[{"name", "quantity", "unit"}]`
- `instructions` as an ordered array of strings
- Infer `prep_time_minutes` and `cook_time_minutes` from context
- `source_type`: `"manual"` for dictated recipes; `recipe_import_url` sets `"url"` automatically

## Tag generously right after adding

Immediately follow `recipe_add` with `tag_add` — cuisine, main ingredient, cooking method, meal category, dietary style. Well-tagged recipes make `recipe_list` filters and `plan_suggest` useful.

## Show visuals when browsing

When the user wants to view or review a recipe, plan, or grocery list, call `display_render` and present the returned HTML path. Don't dump JSON at them.

## Meal planning

Call `plan_suggest` before populating a new plan. Balance across meal categories, respect any dietary constraints the user has mentioned, and favor high-rated or favorited recipes.

## Groceries auto-aggregate

`grocery_generate` normalizes units (tsp → teaspoon, g → gram) and combines duplicates across the plan's recipes — don't pre-process ingredient lists. Pass `servings_multiplier` to scale for a larger group.

## Present results conversationally

Every tool returns JSON. Translate it:
- `{"id": 3, "status": "created"}` → "Saved as **Spaghetti Carbonara** (recipe 3)."
- `{"error": "recipe 99 not found"}` → "I couldn't find recipe 99 — want me to search for something similar?"
- A list → summarize titles, ratings, and tags; offer to render one.

## Logging is automatic

Every mutating tool records itself to chat history. You don't need to call a separate log tool. If you want to attach the user's intent in their own words, pass `user_intent` on the mutating call.
