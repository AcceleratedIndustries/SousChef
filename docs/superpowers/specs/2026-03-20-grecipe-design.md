# grecipe — Recipe Management for Claude Cowork

## Overview

A recipe management system designed to be operated through Claude Cowork on macOS. The user interacts with Claude in natural language; Claude invokes the `grecipe` CLI to manage recipes, meal plans, and grocery lists backed by SQLite. There is no standalone GUI — Claude is the UI.

## Architecture

```
User (Claude Desktop / Cowork) → Claude (Cowork VM) → grecipe CLI → SQLite DB + images/ + HTML output
```

### Components

1. **grecipe CLI** — Python package with subcommands for all recipe operations. All output is JSON by default (for Claude to parse), with `--format text` for human-readable output.
2. **SQLite database** — stores recipes, meal plans, grocery lists, tags, chat history, and recipe modification history.
3. **images/ directory** — dish photos downloaded from scraped URLs, referenced by relative path in the DB.
4. **HTML output** — generated visual pages with dish photos for Cowork to display when browsing recipes or reviewing meal plans.
5. **Claude skill file** — a CLAUDE.md that instructs Claude how to use the CLI, parse input, log interactions, and behave as a recipe assistant.

### Key Design Decisions

- **Claude is the only UI.** No separate app to learn. Natural conversation drives everything.
- **CLI as the bridge.** Clean separation between AI interpretation and data operations. Claude handles natural language; the CLI handles data.
- **Everything in one folder.** DB, images, and output all live in the mounted grecipe directory. Portable and backupable.
- **Chat history logged.** Every interaction that modifies data is recorded in the DB for full traceability.
- **No dependency on Cowork hooks.** Core functionality is self-contained via CLI invocation. Hooks are nice-to-haves if available.

## Data Model

### recipes

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | auto-increment |
| title | TEXT NOT NULL | |
| description | TEXT | short summary of the dish |
| source_url | TEXT | original URL if scraped |
| source_type | TEXT | 'url', 'text', 'other' |
| prep_time_minutes | INTEGER | nullable |
| cook_time_minutes | INTEGER | nullable |
| servings | INTEGER | default serving size |
| ingredients | JSON | array of {name, quantity, unit} |
| instructions | JSON | ordered array of step strings |
| image_path | TEXT | relative path to images/ |
| rating | INTEGER | 1-5, nullable |
| notes | TEXT | personal annotations ("kids loved this", "use less salt") |
| is_favorite | BOOLEAN | default false |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### tags

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| name | TEXT UNIQUE | e.g. "quick", "comfort food" |

### recipe_tags

| Column | Type | Notes |
|--------|------|-------|
| recipe_id | INTEGER FK | |
| tag_id | INTEGER FK | |

### meal_categories

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| name | TEXT UNIQUE | breakfast, lunch, dinner, snack, brunch, dessert, side, appetizer |

### recipe_meal_categories

| Column | Type | Notes |
|--------|------|-------|
| recipe_id | INTEGER FK | |
| meal_category_id | INTEGER FK | |

### dietary_info

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| recipe_id | INTEGER FK | |
| flag | TEXT | gluten-free, dairy-free, nut-free, etc. |

### meal_plans

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| name | TEXT | e.g. "This Week", "Thanksgiving" |
| start_date | DATE | nullable for flexible plans |
| end_date | DATE | nullable |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### meal_plan_items

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| meal_plan_id | INTEGER FK | |
| recipe_id | INTEGER FK | |
| date | DATE | |
| meal_category_id | INTEGER FK | references meal_categories — ensures consistent values |
| servings_override | INTEGER | nullable, overrides recipe default |

### grocery_lists

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| meal_plan_id | INTEGER FK | nullable — standalone lists don't require a meal plan |
| name | TEXT | e.g. "Week of Mar 20" or "Quick run" |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### grocery_items

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| grocery_list_id | INTEGER FK | |
| name | TEXT | ingredient name |
| quantity | REAL | aggregated amount |
| unit | TEXT | |
| store_section | TEXT | produce, dairy, meat, etc. (Claude-inferred) |
| is_checked | BOOLEAN | for shopping |
| source_recipes | JSON | array of recipe IDs that contributed this item |

### chat_log (with FTS5)

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| timestamp | TIMESTAMP | |
| user_message | TEXT | what the user said |
| assistant_response | TEXT | what Claude did/said |
| action_type | TEXT | add_recipe, edit_recipe, create_plan, generate_list, etc. |
| entity_type | TEXT | recipe, plan, grocery_list, etc. |
| entity_id | INTEGER | ID of affected entity |

FTS5 virtual table on `user_message` and `assistant_response` for full-text search.

### recipe_history

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| recipe_id | INTEGER FK | |
| changed_fields | JSON | list of field names changed |
| previous_values | JSON | snapshot of old values |
| chat_log_id | INTEGER FK | links to the conversation that made the change |
| changed_at | TIMESTAMP | |

## CLI Interface

```
grecipe
├── recipe
│   ├── add --json '{...}'            # primary: full recipe as JSON object
│   ├── add --title "..." [--flags]   # convenience: individual flags
│   ├── edit <id> --json '{...}'      # merge-patch: only include fields to change
│   ├── view <id>
│   ├── search "query"               # FTS across titles, ingredients, tags
│   ├── list [--tag X] [--category dinner] [--favorite] [--limit N] [--sort rating|date|title] [--offset N]
│   ├── set-dietary <id> "flag1" "flag2"  # add dietary flags
│   ├── delete <id>
│   ├── rate <id> --rating 4
│   ├── favorite <id>
│   └── import-url <url>             # scrape recipe + image from URL
│
├── tag
│   ├── add <recipe_id> "tag1" "tag2"
│   ├── remove <recipe_id> "tag"
│   └── list
│
├── plan
│   ├── create --name "This Week" [--start DATE] [--end DATE]
│   ├── add <plan_id> <recipe_id> --date DATE --meal breakfast|lunch|dinner|snack
│   ├── remove <plan_id> <item_id>
│   ├── edit <plan_id> --name "..." [--start DATE] [--end DATE]
│   ├── delete <plan_id>
│   ├── view <plan_id>
│   ├── suggest <plan_id>            # recipes not recently planned
│   └── list
│
├── grocery
│   ├── generate <plan_id> [--servings-multiplier N]
│   ├── view <list_id>               # grouped by store section
│   ├── create --name "Quick run"     # standalone list, no meal plan
│   ├── add-item <list_id> --name "milk" [--quantity 1] [--unit gallon] [--section dairy]
│   ├── check <list_id> <item_id>
│   ├── delete <list_id>
│   ├── list                          # all grocery lists
│   └── export <list_id>             # plain text for sharing
│
├── chat
│   ├── log --action "..." --entity-type "..." --entity-id N
│   │       --user-message "..." --assistant-response "..."
│   └── search "query"               # FTS5 search
│
├── display
│   └── render <recipe_id|plan_id>   # generates HTML to output/{recipe|plan}_{id}.html
│
└── db
    ├── init                          # create/migrate database
    └── stats                         # counts and summary info
```

### CLI Design Notes

- All output defaults to JSON. Use `--format text` for human-readable.
- **Primary input mode:** `recipe add --json '{...}'` accepts a full recipe object. This is what Claude uses — it parses natural language into structured JSON, then passes it in one call. Individual flags (`--title`, etc.) exist as a convenience layer.
- **Edit via merge-patch:** `recipe edit <id> --json '{...}'` only requires the fields being changed. Omitted fields are untouched.
- `recipe import-url` handles scraping, image download, and structured extraction in one command. On image download failure, the recipe is stored without an image and a warning is included in the output.
- `plan suggest` checks `meal_plan_items` history to avoid repeating recent meals.
- `display render` generates HTML to `output/{recipe|plan}_{id}.html` for Cowork to display.
- **Unit normalization** (e.g., cups + tablespoons) is handled in the CLI during `grocery generate`, not by Claude.
- **Store section inference** is handled in the CLI using a built-in ingredient-to-section mapping.
- Input methods are extensible — new `recipe import-*` subcommands can be added for photos, screenshots, etc.
- All data-modifying commands accept optional `--log-user-msg` and `--log-assistant-msg` flags for atomic chat logging within the same transaction. The separate `chat log` command exists for logging non-modifying interactions.

## Recipe Input Methods

### Supported Now

1. **Pasted text** — user pastes recipe into chat. Claude parses it into structured fields (title, ingredients as JSON, instructions as JSON, tags, categories) and calls `grecipe recipe add`.
2. **URL scraping** — user shares a recipe URL. `grecipe recipe import-url` scrapes the page for structured recipe data (using recipe schema.org/JSON-LD when available) and downloads the hero image.

### Extensible For Later

- Photo/screenshot import
- Cookbook OCR
- Voice transcription

## Grocery List Intelligence

When generating a grocery list from a meal plan:

1. **Aggregate** — combine same ingredients across recipes
2. **Normalize units** — convert compatible units (e.g., 0.5 cups + 4 tbsp = 0.75 cups)
3. **Group by store section** — Claude infers section from ingredient name (produce, dairy, meat, pantry, frozen, etc.)
4. **Adjust for servings** — apply servings overrides and optional multiplier

## Visual Output

`grecipe display render` generates standalone HTML files with:

- Dish photos from `images/`
- Recipe details (ingredients, instructions, prep/cook time)
- Meal plan calendar view with thumbnails
- Grocery list formatted for printing/sharing

Claude uses these HTML files to show visual content in the Cowork environment.

## Claude Skill File

A `CLAUDE.md` in the project root instructs Claude on:

1. **Identity** — friendly, knowledgeable recipe assistant
2. **Available tools** — full `grecipe` command reference with usage examples
3. **Input parsing** — how to extract structured recipe data from pasted text or URLs
4. **When to show visuals** — generate HTML via `grecipe display render` when browsing, comparing meal plans, or presenting grocery lists
5. **Chat logging** — after every data-modifying action, call `grecipe chat log` to record the interaction
6. **Smart behaviors** — suggest under-used recipes, flag missing images, notice dietary conflicts
7. **Grocery intelligence** — how to infer store sections, combine duplicates, handle unit conversions

## Technology

- **Language:** Python 3.11+
- **Database:** SQLite 3 (with FTS5 for full-text search)
- **CLI framework:** Typer (built on Click, adds type hints, auto-generates help)
- **URL scraping:** httpx + BeautifulSoup4 (with recipe-scrapers library for structured extraction)
- **Image handling:** download to local `images/` directory, store relative paths
- **HTML generation:** Jinja2 templates
- **Packaging:** standard Python package, installable via pip

## What's Out of Scope (For Now)

- Pantry/inventory management (grocery list extensible for this later)
- Standalone web or native GUI
- Multi-user / sharing features
- Cowork hooks integration (conservative approach — investigate during implementation)
- Photo/screenshot recipe import
