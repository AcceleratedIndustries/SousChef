# grecipe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI recipe management system backed by SQLite, designed to be operated by Claude Cowork.

**Architecture:** Python package (`grecipe`) with Typer CLI exposing subcommands for recipes, meal plans, grocery lists, and chat logging. SQLite stores all data with FTS5 for search. Images stored as local files. HTML templates for visual output.

**Tech Stack:** Python 3.11+, Typer, SQLite3 (FTS5), httpx, BeautifulSoup4, recipe-scrapers, Jinja2

**Spec:** `docs/superpowers/specs/2026-03-20-grecipe-design.md`

---

## File Structure

```
grecipe/
├── pyproject.toml                  # package config, dependencies, CLI entry point
├── CLAUDE.md                       # skill file for Cowork
├── src/
│   └── grecipe/
│       ├── __init__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py             # Typer app, top-level group
│       │   ├── recipe.py           # recipe subcommands
│       │   ├── tag.py              # tag subcommands
│       │   ├── plan.py             # meal plan subcommands
│       │   ├── grocery.py          # grocery list subcommands
│       │   ├── chat.py             # chat log subcommands
│       │   ├── display.py          # display render subcommand
│       │   └── db_cmd.py           # db init/stats subcommands
│       ├── db/
│       │   ├── __init__.py
│       │   ├── connection.py       # get_db(), db path resolution
│       │   ├── schema.py           # CREATE TABLE statements, migrations
│       │   └── seed.py             # seed meal_categories
│       ├── models/
│       │   ├── __init__.py
│       │   ├── recipe.py           # recipe CRUD + search
│       │   ├── tag.py              # tag CRUD
│       │   ├── meal_category.py    # meal category lookups
│       │   ├── dietary.py          # dietary flag CRUD
│       │   ├── plan.py             # meal plan CRUD + suggest
│       │   ├── grocery.py          # grocery list CRUD + generate + unit normalization
│       │   ├── chat.py             # chat log CRUD + FTS search
│       │   └── history.py          # recipe history tracking
│       ├── scraper/
│       │   ├── __init__.py
│       │   └── url.py              # URL scraping + image download
│       ├── display/
│       │   ├── __init__.py
│       │   ├── renderer.py         # HTML generation logic
│       │   └── templates/
│       │       ├── recipe.html     # single recipe view
│       │       ├── plan.html       # meal plan calendar view
│       │       └── grocery.html    # grocery list view
│       └── units.py                # unit normalization + store section mapping
├── images/                         # downloaded dish photos
├── output/                         # generated HTML files
├── tests/
│   ├── conftest.py                 # shared fixtures (tmp db, sample data)
│   ├── test_db_schema.py
│   ├── test_recipe_model.py
│   ├── test_tag_model.py
│   ├── test_plan_model.py
│   ├── test_grocery_model.py
│   ├── test_chat_model.py
│   ├── test_history_model.py
│   ├── test_scraper.py
│   ├── test_units.py
│   ├── test_display.py
│   └── test_cli/
│       ├── test_recipe_cli.py
│       ├── test_tag_cli.py
│       ├── test_plan_cli.py
│       ├── test_grocery_cli.py
│       ├── test_chat_cli.py
│       ├── test_display_cli.py
│       └── test_db_cli.py
└── docs/
    └── superpowers/
        ├── specs/
        │   └── 2026-03-20-grecipe-design.md
        └── plans/
            └── 2026-03-20-grecipe-implementation.md
```

---

## Task 1: Project Scaffolding & Database Schema

**Files:**
- Create: `pyproject.toml`
- Create: `src/grecipe/__init__.py`
- Create: `src/grecipe/db/__init__.py`
- Create: `src/grecipe/db/connection.py`
- Create: `src/grecipe/db/schema.py`
- Create: `src/grecipe/db/seed.py`
- Create: `src/grecipe/cli/__init__.py`
- Create: `src/grecipe/cli/main.py`
- Create: `src/grecipe/cli/db_cmd.py`
- Create: `tests/conftest.py`
- Create: `tests/test_db_schema.py`

- [ ] **Step 1: Initialize git repo**

```bash
cd /Users/will/src/grecipe
git init
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "grecipe"
version = "0.1.0"
description = "Recipe management CLI for Claude Cowork"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.15",
    "httpx>=0.28",
    "beautifulsoup4>=4.12",
    "recipe-scrapers>=15.0",
    "jinja2>=3.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=6.0",
]

[project.scripts]
grecipe = "grecipe.cli.main:app"

[tool.hatch.build.targets.wheel]
packages = ["src/grecipe"]
```

- [ ] **Step 3: Create src/grecipe/__init__.py**

```python
"""grecipe — Recipe management for Claude Cowork."""
```

- [ ] **Step 4: Create src/grecipe/db/connection.py**

```python
"""Database connection management."""

import sqlite3
from pathlib import Path

_DEFAULT_DB_DIR = Path.home() / ".grecipe"
_DB_NAME = "grecipe.db"


def get_db_path(db_dir: Path | None = None) -> Path:
    """Return the path to the database file."""
    directory = db_dir or _DEFAULT_DB_DIR
    directory.mkdir(parents=True, exist_ok=True)
    return directory / _DB_NAME


def get_db(db_path: Path | None = None) -> sqlite3.Connection:
    """Return a connection to the database with WAL mode and FK enforcement."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
```

- [ ] **Step 5: Create src/grecipe/db/schema.py**

```python
"""Database schema creation and migration."""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    source_url TEXT,
    source_type TEXT CHECK(source_type IN ('url', 'text', 'other')),
    prep_time_minutes INTEGER,
    cook_time_minutes INTEGER,
    servings INTEGER,
    ingredients JSON,
    instructions JSON,
    image_path TEXT,
    rating INTEGER CHECK(rating BETWEEN 1 AND 5),
    notes TEXT,
    is_favorite BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS recipe_tags (
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (recipe_id, tag_id)
);

CREATE TABLE IF NOT EXISTS meal_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS recipe_meal_categories (
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    meal_category_id INTEGER NOT NULL REFERENCES meal_categories(id) ON DELETE CASCADE,
    PRIMARY KEY (recipe_id, meal_category_id)
);

CREATE TABLE IF NOT EXISTS dietary_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    flag TEXT NOT NULL,
    UNIQUE(recipe_id, flag)
);

CREATE TABLE IF NOT EXISTS meal_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS meal_plan_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meal_plan_id INTEGER NOT NULL REFERENCES meal_plans(id) ON DELETE CASCADE,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    meal_category_id INTEGER NOT NULL REFERENCES meal_categories(id),
    servings_override INTEGER
);

CREATE TABLE IF NOT EXISTS grocery_lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meal_plan_id INTEGER REFERENCES meal_plans(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS grocery_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grocery_list_id INTEGER NOT NULL REFERENCES grocery_lists(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    quantity REAL,
    unit TEXT,
    store_section TEXT,
    is_checked BOOLEAN DEFAULT 0,
    source_recipes JSON
);

CREATE TABLE IF NOT EXISTS chat_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_message TEXT,
    assistant_response TEXT,
    action_type TEXT,
    entity_type TEXT,
    entity_id INTEGER
);

CREATE VIRTUAL TABLE IF NOT EXISTS chat_log_fts USING fts5(
    user_message,
    assistant_response,
    content='chat_log',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS chat_log_ai AFTER INSERT ON chat_log BEGIN
    INSERT INTO chat_log_fts(rowid, user_message, assistant_response)
    VALUES (new.id, new.user_message, new.assistant_response);
END;

CREATE TABLE IF NOT EXISTS recipe_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    changed_fields JSON,
    previous_values JSON,
    chat_log_id INTEGER REFERENCES chat_log(id),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db(conn):
    """Create all tables."""
    conn.executescript(SCHEMA_SQL)
```

- [ ] **Step 6: Create src/grecipe/db/seed.py**

```python
"""Seed data for the database."""

MEAL_CATEGORIES = [
    "breakfast", "lunch", "dinner", "snack",
    "brunch", "dessert", "side", "appetizer",
]


def seed_meal_categories(conn):
    """Insert default meal categories if they don't exist."""
    for name in MEAL_CATEGORIES:
        conn.execute(
            "INSERT OR IGNORE INTO meal_categories (name) VALUES (?)",
            (name,),
        )
    conn.commit()
```

- [ ] **Step 7: Write the failing test for schema creation**

```python
# tests/conftest.py
import sqlite3
import pytest
from pathlib import Path


@pytest.fixture
def db(tmp_path):
    """Provide a fresh in-memory-like DB in a temp directory."""
    from grecipe.db.connection import get_db
    from grecipe.db.schema import init_db
    from grecipe.db.seed import seed_meal_categories

    db_path = tmp_path / "test.db"
    conn = get_db(db_path)
    init_db(conn)
    seed_meal_categories(conn)
    return conn
```

```python
# tests/test_db_schema.py
def test_all_tables_created(db):
    """All expected tables exist after init."""
    cursor = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row["name"] for row in cursor.fetchall()}
    expected = {
        "recipes", "tags", "recipe_tags",
        "meal_categories", "recipe_meal_categories",
        "dietary_info", "meal_plans", "meal_plan_items",
        "grocery_lists", "grocery_items",
        "chat_log", "chat_log_fts", "recipe_history",
    }
    assert expected.issubset(tables)


def test_meal_categories_seeded(db):
    """Default meal categories are populated."""
    cursor = db.execute("SELECT name FROM meal_categories ORDER BY name")
    names = [row["name"] for row in cursor.fetchall()]
    assert "breakfast" in names
    assert "dinner" in names
    assert len(names) == 8


def test_foreign_keys_enabled(db):
    """Foreign key enforcement is on."""
    result = db.execute("PRAGMA foreign_keys").fetchone()
    assert result[0] == 1
```

- [ ] **Step 8: Install the package in dev mode and run tests**

```bash
cd /Users/will/src/grecipe
pip install -e ".[dev]"
pytest tests/test_db_schema.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 9: Create minimal CLI entry point with db init/stats**

```python
# src/grecipe/cli/main.py
"""grecipe CLI entry point."""

import typer

app = typer.Typer(name="grecipe", help="Recipe management for Claude Cowork.")


def register_subcommands():
    from grecipe.cli.db_cmd import app as db_app
    app.add_typer(db_app, name="db")


register_subcommands()

if __name__ == "__main__":
    app()
```

```python
# src/grecipe/cli/db_cmd.py
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
    init_db(conn)
    seed_meal_categories(conn)
    conn.close()
    typer.echo(json.dumps({"status": "ok", "db_path": str(db_path)}))


@app.command()
def stats():
    """Show database statistics."""
    conn = get_db()
    counts = {}
    for table in ["recipes", "tags", "meal_plans", "grocery_lists", "chat_log"]:
        row = conn.execute(f"SELECT COUNT(*) as c FROM {table}").fetchone()
        counts[table] = row["c"]
    conn.close()
    typer.echo(json.dumps(counts))
```

- [ ] **Step 10: Test the CLI manually**

```bash
grecipe db init
grecipe db stats
```

Expected: JSON output with status ok and all zero counts.

- [ ] **Step 11: Create .gitignore and commit**

```bash
cat > /Users/will/src/grecipe/.gitignore << 'EOF'
__pycache__/
*.egg-info/
dist/
.venv/
*.db
images/
output/
.superpowers/
EOF
git add pyproject.toml src/ tests/ docs/ .gitignore
git commit -m "feat: project scaffolding with database schema, seed data, and db CLI"
```

---

## Task 2: Recipe Model (CRUD + Search)

**Files:**
- Create: `src/grecipe/models/__init__.py`
- Create: `src/grecipe/models/recipe.py`
- Create: `tests/test_recipe_model.py`

- [ ] **Step 1: Write failing tests for recipe CRUD**

```python
# tests/test_recipe_model.py
import json
import pytest


def test_add_recipe_from_json(db):
    from grecipe.models.recipe import add_recipe

    recipe_json = {
        "title": "Lemon Chicken",
        "description": "Simple roasted chicken with lemon",
        "source_type": "text",
        "servings": 4,
        "ingredients": [
            {"name": "chicken breast", "quantity": 2, "unit": "lbs"},
            {"name": "lemon", "quantity": 2, "unit": "whole"},
        ],
        "instructions": ["Preheat oven to 400F", "Season chicken", "Roast 25 min"],
    }
    recipe_id = add_recipe(db, recipe_json)
    assert recipe_id == 1


def test_view_recipe(db):
    from grecipe.models.recipe import add_recipe, get_recipe

    recipe_json = {"title": "Pasta", "source_type": "text"}
    rid = add_recipe(db, recipe_json)
    recipe = get_recipe(db, rid)
    assert recipe["title"] == "Pasta"
    assert recipe["id"] == rid


def test_edit_recipe_merge_patch(db):
    from grecipe.models.recipe import add_recipe, edit_recipe, get_recipe

    rid = add_recipe(db, {"title": "Soup", "servings": 4, "source_type": "text"})
    edit_recipe(db, rid, {"title": "Tomato Soup"})
    recipe = get_recipe(db, rid)
    assert recipe["title"] == "Tomato Soup"
    assert recipe["servings"] == 4  # unchanged


def test_delete_recipe(db):
    from grecipe.models.recipe import add_recipe, delete_recipe, get_recipe

    rid = add_recipe(db, {"title": "Delete Me", "source_type": "text"})
    delete_recipe(db, rid)
    assert get_recipe(db, rid) is None


def test_list_recipes(db):
    from grecipe.models.recipe import add_recipe, list_recipes

    add_recipe(db, {"title": "A Recipe", "source_type": "text"})
    add_recipe(db, {"title": "B Recipe", "source_type": "text"})
    results = list_recipes(db)
    assert len(results) == 2


def test_rate_recipe(db):
    from grecipe.models.recipe import add_recipe, rate_recipe, get_recipe

    rid = add_recipe(db, {"title": "Rate Me", "source_type": "text"})
    rate_recipe(db, rid, 5)
    assert get_recipe(db, rid)["rating"] == 5


def test_favorite_recipe(db):
    from grecipe.models.recipe import add_recipe, favorite_recipe, get_recipe

    rid = add_recipe(db, {"title": "Fav Me", "source_type": "text"})
    favorite_recipe(db, rid)
    assert get_recipe(db, rid)["is_favorite"] == 1


def test_list_recipes_with_filters(db):
    from grecipe.models.recipe import add_recipe, favorite_recipe, list_recipes

    r1 = add_recipe(db, {"title": "Fav", "source_type": "text"})
    add_recipe(db, {"title": "Not Fav", "source_type": "text"})
    favorite_recipe(db, r1)
    results = list_recipes(db, favorite=True)
    assert len(results) == 1
    assert results[0]["title"] == "Fav"


def test_search_recipes(db):
    from grecipe.models.recipe import add_recipe, search_recipes

    add_recipe(db, {
        "title": "Spicy Tacos",
        "ingredients": json.dumps([{"name": "ground beef", "quantity": 1, "unit": "lb"}]),
        "source_type": "text",
    })
    add_recipe(db, {"title": "Vanilla Cake", "source_type": "text"})
    results = search_recipes(db, "tacos")
    assert len(results) == 1
    assert results[0]["title"] == "Spicy Tacos"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_recipe_model.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'grecipe.models'`

- [ ] **Step 3: Implement recipe model**

```python
# src/grecipe/models/__init__.py
"""Data models for grecipe."""
```

```python
# src/grecipe/models/recipe.py
"""Recipe CRUD operations."""

from __future__ import annotations

import json
from typing import Any


EDITABLE_FIELDS = {
    "title", "description", "source_url", "source_type",
    "prep_time_minutes", "cook_time_minutes", "servings",
    "ingredients", "instructions", "image_path",
    "rating", "notes", "is_favorite",
}


def add_recipe(conn, data: dict[str, Any]) -> int:
    """Insert a new recipe. Returns the new recipe ID."""
    cols = []
    vals = []
    for key, value in data.items():
        if key in EDITABLE_FIELDS:
            cols.append(key)
            if key in ("ingredients", "instructions") and not isinstance(value, str):
                vals.append(json.dumps(value))
            else:
                vals.append(value)
    placeholders = ", ".join("?" for _ in cols)
    col_names = ", ".join(cols)
    cursor = conn.execute(
        f"INSERT INTO recipes ({col_names}) VALUES ({placeholders})",
        vals,
    )
    conn.commit()
    return cursor.lastrowid


def get_recipe(conn, recipe_id: int) -> dict[str, Any] | None:
    """Get a single recipe by ID."""
    row = conn.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    if row is None:
        return None
    return dict(row)


def edit_recipe(conn, recipe_id: int, changes: dict[str, Any]) -> None:
    """Merge-patch update: only provided fields are changed."""
    sets = []
    vals = []
    for key, value in changes.items():
        if key in EDITABLE_FIELDS:
            sets.append(f"{key} = ?")
            if key in ("ingredients", "instructions") and not isinstance(value, str):
                vals.append(json.dumps(value))
            else:
                vals.append(value)
    if not sets:
        return
    sets.append("updated_at = CURRENT_TIMESTAMP")
    vals.append(recipe_id)
    conn.execute(
        f"UPDATE recipes SET {', '.join(sets)} WHERE id = ?",
        vals,
    )
    conn.commit()


def delete_recipe(conn, recipe_id: int) -> None:
    """Delete a recipe by ID."""
    conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    conn.commit()


def rate_recipe(conn, recipe_id: int, rating: int) -> None:
    """Set a recipe's rating (1-5)."""
    conn.execute(
        "UPDATE recipes SET rating = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (rating, recipe_id),
    )
    conn.commit()


def favorite_recipe(conn, recipe_id: int, value: bool = True) -> None:
    """Toggle a recipe's favorite status."""
    conn.execute(
        "UPDATE recipes SET is_favorite = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (int(value), recipe_id),
    )
    conn.commit()


def list_recipes(
    conn,
    tag: str | None = None,
    category: str | None = None,
    favorite: bool | None = None,
    limit: int = 50,
    offset: int = 0,
    sort: str = "date",
) -> list[dict[str, Any]]:
    """List recipes with optional filters."""
    query = "SELECT r.* FROM recipes r"
    joins = []
    wheres = []
    params = []

    if tag:
        joins.append("JOIN recipe_tags rt ON r.id = rt.recipe_id JOIN tags t ON rt.tag_id = t.id")
        wheres.append("t.name = ?")
        params.append(tag)

    if category:
        joins.append(
            "JOIN recipe_meal_categories rmc ON r.id = rmc.recipe_id "
            "JOIN meal_categories mc ON rmc.meal_category_id = mc.id"
        )
        wheres.append("mc.name = ?")
        params.append(category)

    if favorite is not None:
        wheres.append("r.is_favorite = ?")
        params.append(int(favorite))

    query += " " + " ".join(joins)
    if wheres:
        query += " WHERE " + " AND ".join(wheres)

    sort_map = {"date": "r.created_at DESC", "rating": "r.rating DESC", "title": "r.title ASC"}
    query += f" ORDER BY {sort_map.get(sort, 'r.created_at DESC')}"
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def search_recipes(conn, query: str) -> list[dict[str, Any]]:
    """Full-text search across recipe title, description, and ingredients."""
    # Simple LIKE search — good enough for now, can upgrade to FTS5 later
    pattern = f"%{query}%"
    rows = conn.execute(
        "SELECT * FROM recipes WHERE title LIKE ? OR description LIKE ? OR ingredients LIKE ?",
        (pattern, pattern, pattern),
    ).fetchall()
    return [dict(row) for row in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_recipe_model.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/grecipe/models/ tests/test_recipe_model.py
git commit -m "feat: recipe model with CRUD, search, rating, and favorites"
```

---

## Task 3: Tag & Dietary Models

**Files:**
- Create: `src/grecipe/models/tag.py`
- Create: `src/grecipe/models/dietary.py`
- Create: `src/grecipe/models/meal_category.py`
- Create: `tests/test_tag_model.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_tag_model.py
def test_add_tags_to_recipe(db):
    from grecipe.models.recipe import add_recipe
    from grecipe.models.tag import add_tags, get_tags_for_recipe

    rid = add_recipe(db, {"title": "Tacos", "source_type": "text"})
    add_tags(db, rid, ["mexican", "quick"])
    tags = get_tags_for_recipe(db, rid)
    assert set(tags) == {"mexican", "quick"}


def test_remove_tag_from_recipe(db):
    from grecipe.models.recipe import add_recipe
    from grecipe.models.tag import add_tags, remove_tag, get_tags_for_recipe

    rid = add_recipe(db, {"title": "Tacos", "source_type": "text"})
    add_tags(db, rid, ["mexican", "quick"])
    remove_tag(db, rid, "quick")
    assert get_tags_for_recipe(db, rid) == ["mexican"]


def test_list_all_tags(db):
    from grecipe.models.recipe import add_recipe
    from grecipe.models.tag import add_tags, list_tags

    r1 = add_recipe(db, {"title": "A", "source_type": "text"})
    r2 = add_recipe(db, {"title": "B", "source_type": "text"})
    add_tags(db, r1, ["quick", "easy"])
    add_tags(db, r2, ["quick"])
    tags = list_tags(db)
    assert {"name": "quick", "count": 2} in tags


def test_set_dietary_flags(db):
    from grecipe.models.recipe import add_recipe
    from grecipe.models.dietary import set_dietary, get_dietary

    rid = add_recipe(db, {"title": "Salad", "source_type": "text"})
    set_dietary(db, rid, ["gluten-free", "vegan"])
    flags = get_dietary(db, rid)
    assert set(flags) == {"gluten-free", "vegan"}


def test_set_meal_categories(db):
    from grecipe.models.recipe import add_recipe
    from grecipe.models.meal_category import set_categories, get_categories

    rid = add_recipe(db, {"title": "Eggs", "source_type": "text"})
    set_categories(db, rid, ["breakfast", "brunch"])
    cats = get_categories(db, rid)
    assert set(cats) == {"breakfast", "brunch"}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_tag_model.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement tag, dietary, and meal_category models**

```python
# src/grecipe/models/tag.py
"""Tag CRUD operations."""

from __future__ import annotations
from typing import Any


def add_tags(conn, recipe_id: int, tag_names: list[str]) -> None:
    """Add tags to a recipe, creating tags if needed."""
    for name in tag_names:
        name = name.strip().lower()
        conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
        tag_id = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()["id"]
        conn.execute(
            "INSERT OR IGNORE INTO recipe_tags (recipe_id, tag_id) VALUES (?, ?)",
            (recipe_id, tag_id),
        )
    conn.commit()


def remove_tag(conn, recipe_id: int, tag_name: str) -> None:
    """Remove a tag from a recipe."""
    tag_row = conn.execute("SELECT id FROM tags WHERE name = ?", (tag_name.strip().lower(),)).fetchone()
    if tag_row:
        conn.execute(
            "DELETE FROM recipe_tags WHERE recipe_id = ? AND tag_id = ?",
            (recipe_id, tag_row["id"]),
        )
        conn.commit()


def get_tags_for_recipe(conn, recipe_id: int) -> list[str]:
    """Get all tags for a recipe."""
    rows = conn.execute(
        "SELECT t.name FROM tags t JOIN recipe_tags rt ON t.id = rt.tag_id "
        "WHERE rt.recipe_id = ? ORDER BY t.name",
        (recipe_id,),
    ).fetchall()
    return [row["name"] for row in rows]


def list_tags(conn) -> list[dict[str, Any]]:
    """List all tags with recipe counts."""
    rows = conn.execute(
        "SELECT t.name, COUNT(rt.recipe_id) as count FROM tags t "
        "LEFT JOIN recipe_tags rt ON t.id = rt.tag_id "
        "GROUP BY t.id ORDER BY count DESC"
    ).fetchall()
    return [dict(row) for row in rows]
```

```python
# src/grecipe/models/dietary.py
"""Dietary flag operations."""

from __future__ import annotations


def set_dietary(conn, recipe_id: int, flags: list[str]) -> None:
    """Set dietary flags for a recipe (replaces existing)."""
    conn.execute("DELETE FROM dietary_info WHERE recipe_id = ?", (recipe_id,))
    for flag in flags:
        conn.execute(
            "INSERT INTO dietary_info (recipe_id, flag) VALUES (?, ?)",
            (recipe_id, flag.strip().lower()),
        )
    conn.commit()


def get_dietary(conn, recipe_id: int) -> list[str]:
    """Get dietary flags for a recipe."""
    rows = conn.execute(
        "SELECT flag FROM dietary_info WHERE recipe_id = ? ORDER BY flag",
        (recipe_id,),
    ).fetchall()
    return [row["flag"] for row in rows]
```

```python
# src/grecipe/models/meal_category.py
"""Meal category operations."""

from __future__ import annotations


def set_categories(conn, recipe_id: int, category_names: list[str]) -> None:
    """Set meal categories for a recipe (replaces existing)."""
    conn.execute("DELETE FROM recipe_meal_categories WHERE recipe_id = ?", (recipe_id,))
    for name in category_names:
        row = conn.execute(
            "SELECT id FROM meal_categories WHERE name = ?", (name.strip().lower(),)
        ).fetchone()
        if row:
            conn.execute(
                "INSERT INTO recipe_meal_categories (recipe_id, meal_category_id) VALUES (?, ?)",
                (recipe_id, row["id"]),
            )
    conn.commit()


def get_categories(conn, recipe_id: int) -> list[str]:
    """Get meal categories for a recipe."""
    rows = conn.execute(
        "SELECT mc.name FROM meal_categories mc "
        "JOIN recipe_meal_categories rmc ON mc.id = rmc.meal_category_id "
        "WHERE rmc.recipe_id = ? ORDER BY mc.name",
        (recipe_id,),
    ).fetchall()
    return [row["name"] for row in rows]
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_tag_model.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/grecipe/models/tag.py src/grecipe/models/dietary.py src/grecipe/models/meal_category.py tests/test_tag_model.py
git commit -m "feat: tag, dietary, and meal category models"
```

---

## Task 4: Recipe History & Chat Log Models

**Files:**
- Create: `src/grecipe/models/history.py`
- Create: `src/grecipe/models/chat.py`
- Create: `tests/test_history_model.py`
- Create: `tests/test_chat_model.py`

- [ ] **Step 1: Write failing tests for history**

```python
# tests/test_history_model.py
def test_record_history_on_edit(db):
    from grecipe.models.recipe import add_recipe, get_recipe
    from grecipe.models.history import record_change, get_history

    rid = add_recipe(db, {"title": "Soup", "servings": 4, "source_type": "text"})
    old = get_recipe(db, rid)
    record_change(db, rid, {"title": "Tomato Soup"}, old)
    history = get_history(db, rid)
    assert len(history) == 1
    assert "title" in history[0]["changed_fields"]
    assert history[0]["previous_values"]["title"] == "Soup"
```

- [ ] **Step 2: Write failing tests for chat log**

```python
# tests/test_chat_model.py
def test_log_chat(db):
    from grecipe.models.chat import log_chat, search_chat

    log_chat(db, user_message="add my taco recipe", assistant_response="Added Tacos (id=1)",
             action_type="add_recipe", entity_type="recipe", entity_id=1)
    results = search_chat(db, "taco")
    assert len(results) == 1
    assert results[0]["action_type"] == "add_recipe"


def test_search_chat_no_results(db):
    from grecipe.models.chat import search_chat

    results = search_chat(db, "nonexistent")
    assert results == []
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_history_model.py tests/test_chat_model.py -v
```

Expected: FAIL.

- [ ] **Step 4: Implement history and chat models**

```python
# src/grecipe/models/history.py
"""Recipe history tracking."""

from __future__ import annotations

import json
from typing import Any


def record_change(
    conn, recipe_id: int, changes: dict[str, Any], old_recipe: dict[str, Any],
    chat_log_id: int | None = None,
) -> int:
    """Record a recipe modification."""
    changed_fields = list(changes.keys())
    previous_values = {k: old_recipe.get(k) for k in changed_fields}
    cursor = conn.execute(
        "INSERT INTO recipe_history (recipe_id, changed_fields, previous_values, chat_log_id) "
        "VALUES (?, ?, ?, ?)",
        (recipe_id, json.dumps(changed_fields), json.dumps(previous_values), chat_log_id),
    )
    conn.commit()
    return cursor.lastrowid


def get_history(conn, recipe_id: int) -> list[dict[str, Any]]:
    """Get modification history for a recipe."""
    rows = conn.execute(
        "SELECT * FROM recipe_history WHERE recipe_id = ? ORDER BY changed_at DESC",
        (recipe_id,),
    ).fetchall()
    results = []
    for row in rows:
        d = dict(row)
        d["changed_fields"] = json.loads(d["changed_fields"]) if d["changed_fields"] else []
        d["previous_values"] = json.loads(d["previous_values"]) if d["previous_values"] else {}
        results.append(d)
    return results
```

```python
# src/grecipe/models/chat.py
"""Chat log operations."""

from __future__ import annotations

from typing import Any


def log_chat(
    conn,
    user_message: str | None = None,
    assistant_response: str | None = None,
    action_type: str | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> int:
    """Log a chat interaction. Returns the log entry ID."""
    cursor = conn.execute(
        "INSERT INTO chat_log (user_message, assistant_response, action_type, entity_type, entity_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_message, assistant_response, action_type, entity_type, entity_id),
    )
    conn.commit()
    return cursor.lastrowid


def search_chat(conn, query: str) -> list[dict[str, Any]]:
    """Full-text search across chat history."""
    rows = conn.execute(
        "SELECT cl.* FROM chat_log cl "
        "JOIN chat_log_fts fts ON cl.id = fts.rowid "
        "WHERE chat_log_fts MATCH ? ORDER BY cl.timestamp DESC",
        (query,),
    ).fetchall()
    return [dict(row) for row in rows]
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_history_model.py tests/test_chat_model.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/grecipe/models/history.py src/grecipe/models/chat.py tests/test_history_model.py tests/test_chat_model.py
git commit -m "feat: recipe history tracking and chat log with FTS5 search"
```

---

## Task 5: Meal Plan Model

**Files:**
- Create: `src/grecipe/models/plan.py`
- Create: `tests/test_plan_model.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_plan_model.py
def test_create_plan(db):
    from grecipe.models.plan import create_plan, get_plan

    pid = create_plan(db, name="This Week", start_date="2026-03-20", end_date="2026-03-26")
    plan = get_plan(db, pid)
    assert plan["name"] == "This Week"


def test_add_item_to_plan(db):
    from grecipe.models.recipe import add_recipe
    from grecipe.models.plan import create_plan, add_plan_item, get_plan_items

    rid = add_recipe(db, {"title": "Pasta", "source_type": "text"})
    pid = create_plan(db, name="Week")
    add_plan_item(db, pid, rid, date="2026-03-20", meal_category="dinner")
    items = get_plan_items(db, pid)
    assert len(items) == 1
    assert items[0]["recipe_title"] == "Pasta"


def test_remove_plan_item(db):
    from grecipe.models.recipe import add_recipe
    from grecipe.models.plan import create_plan, add_plan_item, remove_plan_item, get_plan_items

    rid = add_recipe(db, {"title": "Pasta", "source_type": "text"})
    pid = create_plan(db, name="Week")
    item_id = add_plan_item(db, pid, rid, date="2026-03-20", meal_category="dinner")
    remove_plan_item(db, pid, item_id)
    assert get_plan_items(db, pid) == []


def test_delete_plan(db):
    from grecipe.models.plan import create_plan, delete_plan, get_plan

    pid = create_plan(db, name="Delete Me")
    delete_plan(db, pid)
    assert get_plan(db, pid) is None


def test_suggest_recipes(db):
    from grecipe.models.recipe import add_recipe
    from grecipe.models.plan import create_plan, add_plan_item, suggest_recipes

    r1 = add_recipe(db, {"title": "Frequent", "source_type": "text"})
    r2 = add_recipe(db, {"title": "Unused", "source_type": "text"})
    pid = create_plan(db, name="Week")
    add_plan_item(db, pid, r1, date="2026-03-20", meal_category="dinner")
    suggestions = suggest_recipes(db)
    titles = [s["title"] for s in suggestions]
    # Unused should appear before Frequent (less recently used)
    assert titles.index("Unused") < titles.index("Frequent")


def test_list_plans(db):
    from grecipe.models.plan import create_plan, list_plans

    create_plan(db, name="Plan A")
    create_plan(db, name="Plan B")
    plans = list_plans(db)
    assert len(plans) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_plan_model.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement plan model**

```python
# src/grecipe/models/plan.py
"""Meal plan CRUD operations."""

from __future__ import annotations

from typing import Any


def create_plan(
    conn, name: str, start_date: str | None = None, end_date: str | None = None,
) -> int:
    """Create a new meal plan. Returns the plan ID."""
    cursor = conn.execute(
        "INSERT INTO meal_plans (name, start_date, end_date) VALUES (?, ?, ?)",
        (name, start_date, end_date),
    )
    conn.commit()
    return cursor.lastrowid


def get_plan(conn, plan_id: int) -> dict[str, Any] | None:
    """Get a meal plan by ID."""
    row = conn.execute("SELECT * FROM meal_plans WHERE id = ?", (plan_id,)).fetchone()
    return dict(row) if row else None


def edit_plan(
    conn, plan_id: int, name: str | None = None,
    start_date: str | None = None, end_date: str | None = None,
) -> None:
    """Update a meal plan's metadata."""
    sets = ["updated_at = CURRENT_TIMESTAMP"]
    vals = []
    if name is not None:
        sets.append("name = ?")
        vals.append(name)
    if start_date is not None:
        sets.append("start_date = ?")
        vals.append(start_date)
    if end_date is not None:
        sets.append("end_date = ?")
        vals.append(end_date)
    vals.append(plan_id)
    conn.execute(f"UPDATE meal_plans SET {', '.join(sets)} WHERE id = ?", vals)
    conn.commit()


def delete_plan(conn, plan_id: int) -> None:
    """Delete a meal plan and its items."""
    conn.execute("DELETE FROM meal_plans WHERE id = ?", (plan_id,))
    conn.commit()


def add_plan_item(
    conn, plan_id: int, recipe_id: int, date: str, meal_category: str,
    servings_override: int | None = None,
) -> int:
    """Add a recipe to a meal plan. Returns the item ID."""
    cat_row = conn.execute(
        "SELECT id FROM meal_categories WHERE name = ?", (meal_category.lower(),)
    ).fetchone()
    if not cat_row:
        raise ValueError(f"Unknown meal category: {meal_category}")
    cursor = conn.execute(
        "INSERT INTO meal_plan_items (meal_plan_id, recipe_id, date, meal_category_id, servings_override) "
        "VALUES (?, ?, ?, ?, ?)",
        (plan_id, recipe_id, date, cat_row["id"], servings_override),
    )
    conn.execute(
        "UPDATE meal_plans SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (plan_id,)
    )
    conn.commit()
    return cursor.lastrowid


def remove_plan_item(conn, plan_id: int, item_id: int) -> None:
    """Remove an item from a meal plan."""
    conn.execute(
        "DELETE FROM meal_plan_items WHERE id = ? AND meal_plan_id = ?",
        (item_id, plan_id),
    )
    conn.commit()


def get_plan_items(conn, plan_id: int) -> list[dict[str, Any]]:
    """Get all items in a meal plan with recipe titles."""
    rows = conn.execute(
        "SELECT mpi.*, r.title as recipe_title, r.image_path, mc.name as meal_category "
        "FROM meal_plan_items mpi "
        "JOIN recipes r ON mpi.recipe_id = r.id "
        "JOIN meal_categories mc ON mpi.meal_category_id = mc.id "
        "WHERE mpi.meal_plan_id = ? ORDER BY mpi.date, mc.id",
        (plan_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def list_plans(conn) -> list[dict[str, Any]]:
    """List all meal plans."""
    rows = conn.execute(
        "SELECT * FROM meal_plans ORDER BY created_at DESC"
    ).fetchall()
    return [dict(row) for row in rows]


def suggest_recipes(conn, limit: int = 10) -> list[dict[str, Any]]:
    """Suggest recipes that haven't been planned recently."""
    rows = conn.execute(
        "SELECT r.*, MAX(mpi.date) as last_planned "
        "FROM recipes r "
        "LEFT JOIN meal_plan_items mpi ON r.id = mpi.recipe_id "
        "GROUP BY r.id "
        "ORDER BY last_planned ASC NULLS FIRST, r.rating DESC "
        "LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_plan_model.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/grecipe/models/plan.py tests/test_plan_model.py
git commit -m "feat: meal plan model with CRUD, items, and recipe suggestions"
```

---

## Task 6: Grocery Model (with Unit Normalization)

**Files:**
- Create: `src/grecipe/units.py`
- Create: `src/grecipe/models/grocery.py`
- Create: `tests/test_units.py`
- Create: `tests/test_grocery_model.py`

- [ ] **Step 1: Write failing tests for unit normalization**

```python
# tests/test_units.py
from grecipe.units import normalize_unit, can_combine, combine_quantities, infer_store_section


def test_normalize_unit():
    assert normalize_unit("tbsp") == "tablespoon"
    assert normalize_unit("Cups") == "cup"
    assert normalize_unit("oz") == "ounce"


def test_can_combine():
    assert can_combine("cup", "tablespoon") is True
    assert can_combine("cup", "ounce") is False
    assert can_combine("lb", "pound") is True


def test_combine_tablespoons_into_cups():
    qty, unit = combine_quantities(0.5, "cup", 4, "tablespoon")
    assert unit == "cup"
    assert abs(qty - 0.75) < 0.01


def test_infer_store_section():
    assert infer_store_section("chicken breast") == "meat"
    assert infer_store_section("whole milk") == "dairy"
    assert infer_store_section("banana") == "produce"
    assert infer_store_section("olive oil") == "pantry"
```

- [ ] **Step 2: Write failing tests for grocery model**

```python
# tests/test_grocery_model.py
import json


def test_create_standalone_list(db):
    from grecipe.models.grocery import create_list, get_list

    lid = create_list(db, name="Quick run")
    gl = get_list(db, lid)
    assert gl["name"] == "Quick run"
    assert gl["meal_plan_id"] is None


def test_add_item_to_list(db):
    from grecipe.models.grocery import create_list, add_item, get_items

    lid = create_list(db, name="Test")
    add_item(db, lid, name="milk", quantity=1, unit="gallon", store_section="dairy")
    items = get_items(db, lid)
    assert len(items) == 1
    assert items[0]["name"] == "milk"


def test_check_item(db):
    from grecipe.models.grocery import create_list, add_item, check_item, get_items

    lid = create_list(db, name="Test")
    iid = add_item(db, lid, name="eggs")
    check_item(db, lid, iid)
    items = get_items(db, lid)
    assert items[0]["is_checked"] == 1


def test_generate_from_plan(db):
    from grecipe.models.recipe import add_recipe
    from grecipe.models.plan import create_plan, add_plan_item
    from grecipe.models.grocery import generate_from_plan, get_items

    r1 = add_recipe(db, {
        "title": "Pasta",
        "source_type": "text",
        "servings": 2,
        "ingredients": json.dumps([
            {"name": "pasta", "quantity": 8, "unit": "ounce"},
            {"name": "olive oil", "quantity": 2, "unit": "tablespoon"},
        ]),
    })
    r2 = add_recipe(db, {
        "title": "Salad",
        "source_type": "text",
        "servings": 2,
        "ingredients": json.dumps([
            {"name": "olive oil", "quantity": 1, "unit": "tablespoon"},
            {"name": "lettuce", "quantity": 1, "unit": "head"},
        ]),
    })
    pid = create_plan(db, name="Week")
    add_plan_item(db, pid, r1, date="2026-03-20", meal_category="dinner")
    add_plan_item(db, pid, r2, date="2026-03-20", meal_category="dinner")

    lid = generate_from_plan(db, pid)
    items = get_items(db, lid)
    names = {i["name"] for i in items}
    assert "pasta" in names
    assert "olive oil" in names
    assert "lettuce" in names
    # olive oil should be aggregated (2 tbsp + 1 tbsp = 3 tbsp)
    oil = next(i for i in items if i["name"] == "olive oil")
    assert oil["quantity"] == 3.0


def test_delete_list(db):
    from grecipe.models.grocery import create_list, delete_list, get_list

    lid = create_list(db, name="Delete Me")
    delete_list(db, lid)
    assert get_list(db, lid) is None
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_units.py tests/test_grocery_model.py -v
```

Expected: FAIL.

- [ ] **Step 4: Implement units module**

```python
# src/grecipe/units.py
"""Unit normalization and store section inference."""

from __future__ import annotations

# Canonical unit names
UNIT_ALIASES = {
    "tbsp": "tablespoon", "tablespoons": "tablespoon", "tbs": "tablespoon",
    "tsp": "teaspoon", "teaspoons": "teaspoon",
    "cup": "cup", "cups": "cup", "c": "cup",
    "oz": "ounce", "ounces": "ounce",
    "lb": "pound", "lbs": "pound", "pounds": "pound",
    "g": "gram", "grams": "gram",
    "kg": "kilogram", "kilograms": "kilogram",
    "ml": "milliliter", "milliliters": "milliliter",
    "l": "liter", "liters": "liter",
    "whole": "whole", "piece": "whole", "pieces": "whole",
    "head": "head", "heads": "head",
    "clove": "clove", "cloves": "clove",
    "can": "can", "cans": "can",
    "gallon": "gallon", "gallons": "gallon",
    "quart": "quart", "quarts": "quart",
    "pint": "pint", "pints": "pint",
}

# Units that can be combined (convert to base unit)
# Base unit for volume: tablespoon
VOLUME_TO_TBSP = {
    "teaspoon": 1 / 3,
    "tablespoon": 1,
    "cup": 16,
    "pint": 32,
    "quart": 64,
    "gallon": 256,
}

# Base unit for weight: ounce
WEIGHT_TO_OZ = {
    "ounce": 1,
    "pound": 16,
    "gram": 0.035274,
    "kilogram": 35.274,
}


def normalize_unit(unit: str) -> str:
    """Normalize a unit string to its canonical form."""
    return UNIT_ALIASES.get(unit.lower().strip(), unit.lower().strip())


def can_combine(unit1: str, unit2: str) -> bool:
    """Check if two units can be combined."""
    u1 = normalize_unit(unit1)
    u2 = normalize_unit(unit2)
    if u1 == u2:
        return True
    both_volume = u1 in VOLUME_TO_TBSP and u2 in VOLUME_TO_TBSP
    both_weight = u1 in WEIGHT_TO_OZ and u2 in WEIGHT_TO_OZ
    return both_volume or both_weight


def combine_quantities(qty1: float, unit1: str, qty2: float, unit2: str) -> tuple[float, str]:
    """Combine two quantities, converting to the larger unit."""
    u1 = normalize_unit(unit1)
    u2 = normalize_unit(unit2)

    if u1 == u2:
        return qty1 + qty2, u1

    # Volume
    if u1 in VOLUME_TO_TBSP and u2 in VOLUME_TO_TBSP:
        total_tbsp = qty1 * VOLUME_TO_TBSP[u1] + qty2 * VOLUME_TO_TBSP[u2]
        # Use the larger unit
        larger = u1 if VOLUME_TO_TBSP[u1] >= VOLUME_TO_TBSP[u2] else u2
        return total_tbsp / VOLUME_TO_TBSP[larger], larger

    # Weight
    if u1 in WEIGHT_TO_OZ and u2 in WEIGHT_TO_OZ:
        total_oz = qty1 * WEIGHT_TO_OZ[u1] + qty2 * WEIGHT_TO_OZ[u2]
        larger = u1 if WEIGHT_TO_OZ[u1] >= WEIGHT_TO_OZ[u2] else u2
        return total_oz / WEIGHT_TO_OZ[larger], larger

    raise ValueError(f"Cannot combine {unit1} and {unit2}")


# Store section inference — keyword-based mapping
_SECTION_KEYWORDS = {
    "meat": ["chicken", "beef", "pork", "turkey", "lamb", "sausage", "bacon", "steak",
             "ground meat", "ground beef", "ground turkey", "ham", "fish", "salmon",
             "shrimp", "tuna", "crab"],
    "produce": ["lettuce", "tomato", "onion", "garlic", "pepper", "carrot", "celery",
                "potato", "banana", "apple", "lemon", "lime", "avocado", "spinach",
                "broccoli", "cucumber", "mushroom", "herb", "basil", "cilantro",
                "parsley", "ginger", "corn", "zucchini", "squash", "berry",
                "strawberry", "blueberry", "orange", "mango"],
    "dairy": ["milk", "cheese", "butter", "cream", "yogurt", "sour cream",
              "egg", "eggs", "parmesan", "mozzarella", "cheddar"],
    "pantry": ["oil", "vinegar", "salt", "pepper", "sugar", "flour", "rice",
               "pasta", "noodle", "sauce", "broth", "stock", "spice", "cumin",
               "paprika", "cinnamon", "vanilla", "baking", "soy sauce",
               "honey", "maple", "mustard", "ketchup", "mayo"],
    "bakery": ["bread", "tortilla", "bun", "roll", "pita", "naan"],
    "frozen": ["frozen", "ice cream"],
    "canned": ["canned", "can of", "beans", "chickpea", "lentil"],
}


def infer_store_section(ingredient_name: str) -> str:
    """Infer the store section from an ingredient name."""
    name_lower = ingredient_name.lower()
    for section, keywords in _SECTION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in name_lower:
                return section
    return "other"
```

- [ ] **Step 5: Implement grocery model**

```python
# src/grecipe/models/grocery.py
"""Grocery list operations."""

from __future__ import annotations

import json
from typing import Any

from grecipe.units import normalize_unit, can_combine, combine_quantities, infer_store_section


def create_list(conn, name: str, meal_plan_id: int | None = None) -> int:
    """Create a grocery list. Returns the list ID."""
    cursor = conn.execute(
        "INSERT INTO grocery_lists (name, meal_plan_id) VALUES (?, ?)",
        (name, meal_plan_id),
    )
    conn.commit()
    return cursor.lastrowid


def get_list(conn, list_id: int) -> dict[str, Any] | None:
    """Get a grocery list by ID."""
    row = conn.execute("SELECT * FROM grocery_lists WHERE id = ?", (list_id,)).fetchone()
    return dict(row) if row else None


def delete_list(conn, list_id: int) -> None:
    """Delete a grocery list."""
    conn.execute("DELETE FROM grocery_lists WHERE id = ?", (list_id,))
    conn.commit()


def list_lists(conn) -> list[dict[str, Any]]:
    """List all grocery lists."""
    rows = conn.execute("SELECT * FROM grocery_lists ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def add_item(
    conn, list_id: int, name: str, quantity: float | None = None,
    unit: str | None = None, store_section: str | None = None,
) -> int:
    """Add an item to a grocery list."""
    section = store_section or infer_store_section(name)
    cursor = conn.execute(
        "INSERT INTO grocery_items (grocery_list_id, name, quantity, unit, store_section) "
        "VALUES (?, ?, ?, ?, ?)",
        (list_id, name, quantity, unit, section),
    )
    conn.commit()
    return cursor.lastrowid


def check_item(conn, list_id: int, item_id: int, checked: bool = True) -> None:
    """Mark/unmark a grocery item as checked."""
    conn.execute(
        "UPDATE grocery_items SET is_checked = ? WHERE id = ? AND grocery_list_id = ?",
        (int(checked), item_id, list_id),
    )
    conn.commit()


def get_items(conn, list_id: int) -> list[dict[str, Any]]:
    """Get all items in a grocery list, grouped by store section."""
    rows = conn.execute(
        "SELECT * FROM grocery_items WHERE grocery_list_id = ? ORDER BY store_section, name",
        (list_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def export_list(conn, list_id: int) -> str:
    """Export a grocery list as plain text grouped by section."""
    items = get_items(conn, list_id)
    gl = get_list(conn, list_id)
    lines = [f"# {gl['name']}", ""]
    current_section = None
    for item in items:
        if item["store_section"] != current_section:
            current_section = item["store_section"]
            lines.append(f"## {(current_section or 'Other').title()}")
        check = "x" if item["is_checked"] else " "
        qty_str = ""
        if item["quantity"]:
            qty_str = f" ({item['quantity']}"
            if item["unit"]:
                qty_str += f" {item['unit']}"
            qty_str += ")"
        lines.append(f"- [{check}] {item['name']}{qty_str}")
    return "\n".join(lines)


def generate_from_plan(
    conn, plan_id: int, servings_multiplier: float = 1.0,
) -> int:
    """Generate a grocery list from a meal plan by aggregating ingredients."""
    plan = conn.execute("SELECT * FROM meal_plans WHERE id = ?", (plan_id,)).fetchone()
    if not plan:
        raise ValueError(f"Plan {plan_id} not found")

    # Gather all ingredients from plan items
    items_rows = conn.execute(
        "SELECT mpi.*, r.ingredients, r.servings, r.id as rid "
        "FROM meal_plan_items mpi JOIN recipes r ON mpi.recipe_id = r.id "
        "WHERE mpi.meal_plan_id = ?",
        (plan_id,),
    ).fetchall()

    # Aggregate ingredients
    aggregated: dict[str, dict] = {}  # key: normalized ingredient name

    for item in items_rows:
        ingredients_json = item["ingredients"]
        if not ingredients_json:
            continue
        ingredients = json.loads(ingredients_json) if isinstance(ingredients_json, str) else ingredients_json
        recipe_servings = item["servings"] or 1
        override = item["servings_override"] or recipe_servings
        scale = (override / recipe_servings) * servings_multiplier

        for ing in ingredients:
            name = ing["name"].lower().strip()
            qty = (ing.get("quantity") or 0) * scale
            unit = normalize_unit(ing.get("unit", "")) if ing.get("unit") else ""

            if name in aggregated:
                existing = aggregated[name]
                if existing["unit"] and unit and can_combine(existing["unit"], unit):
                    combined_qty, combined_unit = combine_quantities(
                        existing["quantity"], existing["unit"], qty, unit
                    )
                    existing["quantity"] = combined_qty
                    existing["unit"] = combined_unit
                elif existing["unit"] == unit:
                    existing["quantity"] += qty
                else:
                    # Can't combine — just add the quantity to existing
                    existing["quantity"] += qty
                existing["source_recipes"].add(item["rid"])
            else:
                aggregated[name] = {
                    "quantity": qty,
                    "unit": unit,
                    "source_recipes": {item["rid"]},
                }

    # Create the grocery list
    list_name = f"Groceries for {plan['name']}"
    lid = create_list(conn, name=list_name, meal_plan_id=plan_id)

    for name, info in sorted(aggregated.items()):
        section = infer_store_section(name)
        conn.execute(
            "INSERT INTO grocery_items (grocery_list_id, name, quantity, unit, store_section, source_recipes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (lid, name, round(info["quantity"], 2), info["unit"] or None, section,
             json.dumps(list(info["source_recipes"]))),
        )
    conn.commit()
    return lid
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_units.py tests/test_grocery_model.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/grecipe/units.py src/grecipe/models/grocery.py tests/test_units.py tests/test_grocery_model.py
git commit -m "feat: grocery model with unit normalization, aggregation, and store section inference"
```

---

## Task 7: URL Scraper

**Files:**
- Create: `src/grecipe/scraper/__init__.py`
- Create: `src/grecipe/scraper/url.py`
- Create: `tests/test_scraper.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_scraper.py
import json
from unittest.mock import patch, MagicMock
from grecipe.scraper.url import scrape_recipe, download_image


def test_scrape_recipe_with_recipe_scrapers():
    """Test scraping with recipe-scrapers library."""
    mock_scraper = MagicMock()
    mock_scraper.title.return_value = "Test Chicken"
    mock_scraper.ingredients.return_value = ["2 lbs chicken", "1 lemon"]
    mock_scraper.instructions_list.return_value = ["Preheat oven", "Cook chicken"]
    mock_scraper.image.return_value = "https://example.com/chicken.jpg"
    mock_scraper.total_time.return_value = 45
    mock_scraper.yields.return_value = "4 servings"

    with patch("grecipe.scraper.url.scrape_html") as mock_scrape:
        mock_scrape.return_value = mock_scraper
        result = scrape_recipe("https://example.com/recipe", "<html></html>")

    assert result["title"] == "Test Chicken"
    assert result["image_url"] == "https://example.com/chicken.jpg"
    assert len(result["instructions"]) == 2


def test_download_image_success(tmp_path):
    """Test successful image download."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"fake image data"
    mock_response.headers = {"content-type": "image/jpeg"}

    with patch("grecipe.scraper.url.httpx.get", return_value=mock_response):
        path = download_image("https://example.com/img.jpg", tmp_path)

    assert path is not None
    assert path.exists()
    assert path.read_bytes() == b"fake image data"


def test_download_image_failure(tmp_path):
    """Test graceful failure on image download error."""
    with patch("grecipe.scraper.url.httpx.get", side_effect=Exception("timeout")):
        path = download_image("https://example.com/img.jpg", tmp_path)

    assert path is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_scraper.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement scraper**

```python
# src/grecipe/scraper/__init__.py
"""Recipe scraping utilities."""
```

```python
# src/grecipe/scraper/url.py
"""URL-based recipe scraping and image download."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import httpx
from recipe_scrapers import scrape_html


def scrape_recipe(url: str, html: str) -> dict[str, Any]:
    """Extract structured recipe data from HTML using recipe-scrapers."""
    scraper = scrape_html(html=html, org_url=url)

    # Parse yields into a number
    servings = None
    try:
        yields = scraper.yields()
        if yields:
            match = re.search(r"(\d+)", yields)
            if match:
                servings = int(match.group(1))
    except Exception:
        pass

    # Parse total time
    total_time = None
    try:
        total_time = scraper.total_time()
    except Exception:
        pass

    # Get image URL
    image_url = None
    try:
        image_url = scraper.image()
    except Exception:
        pass

    return {
        "title": scraper.title(),
        "ingredients_raw": scraper.ingredients(),
        "instructions": scraper.instructions_list(),
        "image_url": image_url,
        "total_time_minutes": total_time,
        "servings": servings,
        "source_url": url,
    }


def download_image(url: str, images_dir: Path) -> Path | None:
    """Download an image to the images directory. Returns path on success, None on failure."""
    try:
        response = httpx.get(url, timeout=30, follow_redirects=True)
        response.raise_for_status()
    except Exception:
        return None

    # Determine extension from content-type
    content_type = response.headers.get("content-type", "")
    ext = ".jpg"
    if "png" in content_type:
        ext = ".png"
    elif "webp" in content_type:
        ext = ".webp"
    elif "gif" in content_type:
        ext = ".gif"

    # Use URL hash as filename to avoid collisions
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:12]
    filename = f"{url_hash}{ext}"
    filepath = images_dir / filename

    images_dir.mkdir(parents=True, exist_ok=True)
    filepath.write_bytes(response.content)
    return filepath


def fetch_and_scrape(url: str, images_dir: Path) -> dict[str, Any]:
    """Fetch a URL, scrape the recipe, and download the image."""
    response = httpx.get(url, timeout=30, follow_redirects=True)
    response.raise_for_status()

    result = scrape_recipe(url, response.text)

    image_path = None
    if result.get("image_url"):
        downloaded = download_image(result["image_url"], images_dir)
        if downloaded:
            image_path = str(downloaded.relative_to(images_dir.parent))

    result["image_path"] = image_path
    return result
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_scraper.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/grecipe/scraper/ tests/test_scraper.py
git commit -m "feat: URL recipe scraper with image download"
```

---

## Task 8: HTML Display Renderer

**Files:**
- Create: `src/grecipe/display/__init__.py`
- Create: `src/grecipe/display/renderer.py`
- Create: `src/grecipe/display/templates/recipe.html`
- Create: `src/grecipe/display/templates/plan.html`
- Create: `src/grecipe/display/templates/grocery.html`
- Create: `tests/test_display.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_display.py
import json
from pathlib import Path


def test_render_recipe(db, tmp_path):
    from grecipe.models.recipe import add_recipe
    from grecipe.display.renderer import render_recipe

    rid = add_recipe(db, {
        "title": "Test Pasta",
        "description": "A simple pasta",
        "servings": 4,
        "source_type": "text",
        "ingredients": json.dumps([{"name": "pasta", "quantity": 8, "unit": "oz"}]),
        "instructions": json.dumps(["Boil water", "Cook pasta"]),
    })
    output = render_recipe(db, rid, output_dir=tmp_path)
    assert output.exists()
    html = output.read_text()
    assert "Test Pasta" in html
    assert "pasta" in html


def test_render_plan(db, tmp_path):
    from grecipe.models.recipe import add_recipe
    from grecipe.models.plan import create_plan, add_plan_item
    from grecipe.display.renderer import render_plan

    rid = add_recipe(db, {"title": "Tacos", "source_type": "text"})
    pid = create_plan(db, name="Test Week")
    add_plan_item(db, pid, rid, date="2026-03-20", meal_category="dinner")
    output = render_plan(db, pid, output_dir=tmp_path)
    assert output.exists()
    html = output.read_text()
    assert "Test Week" in html
    assert "Tacos" in html


def test_render_grocery(db, tmp_path):
    from grecipe.models.grocery import create_list, add_item
    from grecipe.display.renderer import render_grocery

    lid = create_list(db, name="Shopping")
    add_item(db, lid, name="milk", quantity=1, unit="gallon", store_section="dairy")
    output = render_grocery(db, lid, output_dir=tmp_path)
    assert output.exists()
    html = output.read_text()
    assert "Shopping" in html
    assert "milk" in html
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_display.py -v
```

Expected: FAIL.

- [ ] **Step 3: Create Jinja2 templates**

```html
<!-- src/grecipe/display/templates/recipe.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ recipe.title }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; color: #333; }
        h1 { color: #2d3748; }
        .meta { color: #718096; margin-bottom: 1.5rem; }
        .meta span { margin-right: 1.5rem; }
        img { max-width: 100%; border-radius: 12px; margin: 1rem 0; }
        .ingredients { background: #f7fafc; padding: 1.5rem; border-radius: 8px; margin: 1rem 0; }
        .ingredients li { margin: 0.5rem 0; }
        .instructions ol { line-height: 1.8; }
        .notes { background: #fffff0; padding: 1rem; border-left: 4px solid #ecc94b; margin: 1rem 0; }
        .tags { margin: 1rem 0; }
        .tag { display: inline-block; background: #e2e8f0; padding: 0.25rem 0.75rem; border-radius: 9999px; margin: 0.25rem; font-size: 0.875rem; }
    </style>
</head>
<body>
    <h1>{{ recipe.title }}</h1>
    {% if recipe.description %}<p>{{ recipe.description }}</p>{% endif %}
    {% if recipe.image_path %}<img src="../{{ recipe.image_path }}" alt="{{ recipe.title }}">{% endif %}
    <div class="meta">
        {% if recipe.servings %}<span>Servings: {{ recipe.servings }}</span>{% endif %}
        {% if recipe.prep_time_minutes %}<span>Prep: {{ recipe.prep_time_minutes }}min</span>{% endif %}
        {% if recipe.cook_time_minutes %}<span>Cook: {{ recipe.cook_time_minutes }}min</span>{% endif %}
        {% if recipe.rating %}<span>Rating: {{ "★" * recipe.rating }}{{ "☆" * (5 - recipe.rating) }}</span>{% endif %}
    </div>
    {% if tags %}<div class="tags">{% for t in tags %}<span class="tag">{{ t }}</span>{% endfor %}</div>{% endif %}
    {% if ingredients %}
    <div class="ingredients">
        <h2>Ingredients</h2>
        <ul>
        {% for ing in ingredients %}
            <li>{{ ing.quantity }} {{ ing.unit }} {{ ing.name }}</li>
        {% endfor %}
        </ul>
    </div>
    {% endif %}
    {% if instructions %}
    <div class="instructions">
        <h2>Instructions</h2>
        <ol>
        {% for step in instructions %}
            <li>{{ step }}</li>
        {% endfor %}
        </ol>
    </div>
    {% endif %}
    {% if recipe.notes %}<div class="notes"><strong>Notes:</strong> {{ recipe.notes }}</div>{% endif %}
</body>
</html>
```

```html
<!-- src/grecipe/display/templates/plan.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ plan.name }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; color: #333; }
        h1 { color: #2d3748; }
        .day { background: #f7fafc; padding: 1rem 1.5rem; border-radius: 8px; margin: 1rem 0; }
        .day h3 { margin: 0 0 0.5rem 0; color: #4a5568; }
        .meal { display: flex; align-items: center; margin: 0.5rem 0; }
        .meal-type { font-weight: 600; width: 100px; color: #718096; }
        .meal img { width: 60px; height: 60px; object-fit: cover; border-radius: 8px; margin-right: 1rem; }
    </style>
</head>
<body>
    <h1>{{ plan.name }}</h1>
    {% if plan.start_date %}<p>{{ plan.start_date }} — {{ plan.end_date }}</p>{% endif %}
    {% for date, meals in days.items() %}
    <div class="day">
        <h3>{{ date }}</h3>
        {% for meal in meals %}
        <div class="meal">
            <span class="meal-type">{{ meal.meal_category }}</span>
            {% if meal.image_path %}<img src="../{{ meal.image_path }}" alt="{{ meal.recipe_title }}">{% endif %}
            <span>{{ meal.recipe_title }}</span>
        </div>
        {% endfor %}
    </div>
    {% endfor %}
</body>
</html>
```

```html
<!-- src/grecipe/display/templates/grocery.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ grocery_list.name }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 600px; margin: 2rem auto; padding: 0 1rem; color: #333; }
        h1 { color: #2d3748; }
        h2 { color: #4a5568; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.5rem; }
        .item { display: flex; align-items: center; padding: 0.5rem 0; }
        .item.checked { text-decoration: line-through; color: #a0aec0; }
        .qty { color: #718096; margin-left: auto; font-size: 0.875rem; }
    </style>
</head>
<body>
    <h1>{{ grocery_list.name }}</h1>
    {% for section, items in sections.items() %}
    <h2>{{ section | title }}</h2>
    {% for item in items %}
    <div class="item {% if item.is_checked %}checked{% endif %}">
        <span>{{ item.name }}</span>
        {% if item.quantity %}<span class="qty">{{ item.quantity }} {{ item.unit or '' }}</span>{% endif %}
    </div>
    {% endfor %}
    {% endfor %}
</body>
</html>
```

- [ ] **Step 4: Implement renderer**

```python
# src/grecipe/display/__init__.py
"""Display and HTML rendering."""
```

```python
# src/grecipe/display/renderer.py
"""HTML rendering for recipes, plans, and grocery lists."""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from grecipe.models.recipe import get_recipe
from grecipe.models.tag import get_tags_for_recipe
from grecipe.models.plan import get_plan, get_plan_items
from grecipe.models.grocery import get_list, get_items

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _get_env() -> Environment:
    return Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=True)


def render_recipe(conn, recipe_id: int, output_dir: Path) -> Path:
    """Render a recipe to an HTML file."""
    recipe = get_recipe(conn, recipe_id)
    tags = get_tags_for_recipe(conn, recipe_id)

    ingredients = []
    if recipe.get("ingredients"):
        raw = recipe["ingredients"]
        ingredients = json.loads(raw) if isinstance(raw, str) else raw

    instructions = []
    if recipe.get("instructions"):
        raw = recipe["instructions"]
        instructions = json.loads(raw) if isinstance(raw, str) else raw

    env = _get_env()
    template = env.get_template("recipe.html")
    html = template.render(recipe=recipe, tags=tags, ingredients=ingredients, instructions=instructions)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"recipe_{recipe_id}.html"
    output_path.write_text(html)
    return output_path


def render_plan(conn, plan_id: int, output_dir: Path) -> Path:
    """Render a meal plan to an HTML file."""
    plan = get_plan(conn, plan_id)
    items = get_plan_items(conn, plan_id)

    days: OrderedDict[str, list] = OrderedDict()
    for item in items:
        date = item["date"]
        if date not in days:
            days[date] = []
        days[date].append(item)

    env = _get_env()
    template = env.get_template("plan.html")
    html = template.render(plan=plan, days=days)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"plan_{plan_id}.html"
    output_path.write_text(html)
    return output_path


def render_grocery(conn, list_id: int, output_dir: Path) -> Path:
    """Render a grocery list to an HTML file."""
    grocery_list = get_list(conn, list_id)
    items = get_items(conn, list_id)

    sections: OrderedDict[str, list] = OrderedDict()
    for item in items:
        section = item.get("store_section") or "other"
        if section not in sections:
            sections[section] = []
        sections[section].append(item)

    env = _get_env()
    template = env.get_template("grocery.html")
    html = template.render(grocery_list=grocery_list, sections=sections)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"grocery_{list_id}.html"
    output_path.write_text(html)
    return output_path
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_display.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/grecipe/display/ tests/test_display.py
git commit -m "feat: HTML renderer for recipes, meal plans, and grocery lists"
```

---

## Task 9: CLI Commands — Recipe, Tag, Dietary

**Files:**
- Create: `src/grecipe/cli/recipe.py`
- Create: `src/grecipe/cli/tag.py`
- Modify: `src/grecipe/cli/main.py`
- Create: `tests/test_cli/test_recipe_cli.py`
- Create: `tests/test_cli/test_tag_cli.py`

- [ ] **Step 1: Write failing CLI tests**

```python
# tests/test_cli/test_recipe_cli.py
import json
from typer.testing import CliRunner
from grecipe.cli.main import app

runner = CliRunner()


def test_db_init_then_recipe_add(tmp_path, monkeypatch):
    monkeypatch.setenv("GRECIPE_DB_DIR", str(tmp_path))
    result = runner.invoke(app, ["db", "init"])
    assert result.exit_code == 0

    recipe = json.dumps({"title": "Tacos", "source_type": "text", "servings": 4})
    result = runner.invoke(app, ["recipe", "add", "--json", recipe])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["id"] == 1


def test_recipe_view(tmp_path, monkeypatch):
    monkeypatch.setenv("GRECIPE_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    recipe = json.dumps({"title": "Pasta", "source_type": "text"})
    runner.invoke(app, ["recipe", "add", "--json", recipe])

    result = runner.invoke(app, ["recipe", "view", "1"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["title"] == "Pasta"


def test_recipe_list(tmp_path, monkeypatch):
    monkeypatch.setenv("GRECIPE_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    runner.invoke(app, ["recipe", "add", "--json", json.dumps({"title": "A", "source_type": "text"})])
    runner.invoke(app, ["recipe", "add", "--json", json.dumps({"title": "B", "source_type": "text"})])

    result = runner.invoke(app, ["recipe", "list"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) == 2


def test_recipe_edit(tmp_path, monkeypatch):
    monkeypatch.setenv("GRECIPE_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    runner.invoke(app, ["recipe", "add", "--json", json.dumps({"title": "Old", "source_type": "text"})])

    result = runner.invoke(app, ["recipe", "edit", "1", "--json", json.dumps({"title": "New"})])
    assert result.exit_code == 0

    result = runner.invoke(app, ["recipe", "view", "1"])
    data = json.loads(result.stdout)
    assert data["title"] == "New"


def test_recipe_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("GRECIPE_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    runner.invoke(app, ["recipe", "add", "--json", json.dumps({"title": "Gone", "source_type": "text"})])

    result = runner.invoke(app, ["recipe", "delete", "1"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["recipe", "list"])
    data = json.loads(result.stdout)
    assert len(data) == 0
```

```python
# tests/test_cli/test_tag_cli.py
import json
from typer.testing import CliRunner
from grecipe.cli.main import app

runner = CliRunner()


def test_tag_add_and_list(tmp_path, monkeypatch):
    monkeypatch.setenv("GRECIPE_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    runner.invoke(app, ["recipe", "add", "--json", json.dumps({"title": "Tacos", "source_type": "text"})])

    result = runner.invoke(app, ["tag", "add", "1", "mexican", "quick"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["tag", "list"])
    data = json.loads(result.stdout)
    assert len(data) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_cli/ -v
```

Expected: FAIL.

- [ ] **Step 3: Implement recipe and tag CLI commands**

Update `src/grecipe/db/connection.py` to support `GRECIPE_DB_DIR` env var:

```python
# Add to connection.py — replace get_db_path:
import os

def get_db_path(db_dir: Path | None = None) -> Path:
    """Return the path to the database file."""
    if db_dir is None:
        env_dir = os.environ.get("GRECIPE_DB_DIR")
        directory = Path(env_dir) if env_dir else _DEFAULT_DB_DIR
    else:
        directory = db_dir
    directory.mkdir(parents=True, exist_ok=True)
    return directory / _DB_NAME
```

```python
# src/grecipe/cli/recipe.py
"""Recipe CLI commands."""

import json
from typing import Optional

import typer

from grecipe.db.connection import get_db
from grecipe.models.recipe import (
    add_recipe, get_recipe, edit_recipe, delete_recipe,
    list_recipes, search_recipes, rate_recipe, favorite_recipe,
)
from grecipe.models.history import record_change
from grecipe.models.dietary import set_dietary
from grecipe.models.chat import log_chat
from grecipe.scraper.url import fetch_and_scrape

app = typer.Typer(help="Recipe management.")


def _output(data):
    typer.echo(json.dumps(data, default=str))


@app.command("add")
def add(
    recipe_json: Optional[str] = typer.Option(None, "--json", help="Full recipe as JSON"),
    title: Optional[str] = typer.Option(None, "--title"),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Add a new recipe."""
    conn = get_db()
    if recipe_json:
        data = json.loads(recipe_json)
    elif title:
        data = {"title": title}
    else:
        typer.echo(json.dumps({"error": "Provide --json or --title"}))
        raise typer.Exit(1)

    recipe_id = add_recipe(conn, data)
    if log_user_msg or log_assistant_msg:
        log_chat(conn, user_message=log_user_msg, assistant_response=log_assistant_msg,
                 action_type="add_recipe", entity_type="recipe", entity_id=recipe_id)
    conn.close()
    _output({"id": recipe_id, "status": "created"})


@app.command("view")
def view(recipe_id: int):
    """View a recipe by ID."""
    conn = get_db()
    recipe = get_recipe(conn, recipe_id)
    conn.close()
    if recipe:
        _output(recipe)
    else:
        _output({"error": f"Recipe {recipe_id} not found"})
        raise typer.Exit(1)


@app.command("edit")
def edit(
    recipe_id: int,
    changes_json: str = typer.Option(..., "--json", help="Fields to change as JSON"),
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Edit a recipe (merge-patch)."""
    conn = get_db()
    old = get_recipe(conn, recipe_id)
    if not old:
        _output({"error": f"Recipe {recipe_id} not found"})
        raise typer.Exit(1)
    changes = json.loads(changes_json)
    edit_recipe(conn, recipe_id, changes)
    record_change(conn, recipe_id, changes, old)
    if log_user_msg or log_assistant_msg:
        log_chat(conn, user_message=log_user_msg, assistant_response=log_assistant_msg,
                 action_type="edit_recipe", entity_type="recipe", entity_id=recipe_id)
    conn.close()
    _output({"id": recipe_id, "status": "updated"})


@app.command("list")
def list_cmd(
    tag: Optional[str] = typer.Option(None, "--tag"),
    category: Optional[str] = typer.Option(None, "--category"),
    favorite: Optional[bool] = typer.Option(None, "--favorite"),
    limit: int = typer.Option(50, "--limit"),
    offset: int = typer.Option(0, "--offset"),
    sort: str = typer.Option("date", "--sort"),
):
    """List recipes with filters."""
    conn = get_db()
    results = list_recipes(conn, tag=tag, category=category, favorite=favorite,
                           limit=limit, offset=offset, sort=sort)
    conn.close()
    _output(results)


@app.command("search")
def search(query: str):
    """Search recipes."""
    conn = get_db()
    results = search_recipes(conn, query)
    conn.close()
    _output(results)


@app.command("delete")
def delete(
    recipe_id: int,
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Delete a recipe."""
    conn = get_db()
    delete_recipe(conn, recipe_id)
    if log_user_msg or log_assistant_msg:
        log_chat(conn, user_message=log_user_msg, assistant_response=log_assistant_msg,
                 action_type="delete_recipe", entity_type="recipe", entity_id=recipe_id)
    conn.close()
    _output({"id": recipe_id, "status": "deleted"})


@app.command("rate")
def rate(recipe_id: int, rating: int = typer.Option(..., "--rating")):
    """Rate a recipe 1-5."""
    conn = get_db()
    rate_recipe(conn, recipe_id, rating)
    conn.close()
    _output({"id": recipe_id, "rating": rating})


@app.command("favorite")
def fav(recipe_id: int):
    """Toggle favorite on a recipe."""
    conn = get_db()
    recipe = get_recipe(conn, recipe_id)
    new_val = not bool(recipe["is_favorite"]) if recipe else True
    favorite_recipe(conn, recipe_id, new_val)
    conn.close()
    _output({"id": recipe_id, "is_favorite": new_val})


@app.command("set-dietary")
def set_dietary_cmd(recipe_id: int, flags: list[str]):
    """Set dietary flags for a recipe."""
    conn = get_db()
    set_dietary(conn, recipe_id, flags)
    conn.close()
    _output({"id": recipe_id, "dietary": flags})


@app.command("import-url")
def import_url(
    url: str,
    log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
    log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
):
    """Import a recipe from a URL."""
    from pathlib import Path
    conn = get_db()
    db_path = Path(conn.execute("PRAGMA database_list").fetchone()["file"]).parent
    images_dir = db_path / "images"
    result = fetch_and_scrape(url, images_dir)

    recipe_data = {
        "title": result["title"],
        "source_url": result["source_url"],
        "source_type": "url",
        "servings": result.get("servings"),
        "instructions": result.get("instructions", []),
        "image_path": result.get("image_path"),
    }
    # Store raw ingredients for Claude to parse further if needed
    if result.get("ingredients_raw"):
        recipe_data["ingredients"] = [{"name": i, "quantity": None, "unit": None}
                                      for i in result["ingredients_raw"]]

    recipe_id = add_recipe(conn, recipe_data)
    if log_user_msg or log_assistant_msg:
        log_chat(conn, user_message=log_user_msg, assistant_response=log_assistant_msg,
                 action_type="import_recipe", entity_type="recipe", entity_id=recipe_id)
    conn.close()
    _output({"id": recipe_id, "title": result["title"], "status": "imported"})
```

```python
# src/grecipe/cli/tag.py
"""Tag CLI commands."""

import json
import typer

from grecipe.db.connection import get_db
from grecipe.models.tag import add_tags, remove_tag, list_tags

app = typer.Typer(help="Tag management.")


@app.command("add")
def add(recipe_id: int, tags: list[str]):
    """Add tags to a recipe."""
    conn = get_db()
    add_tags(conn, recipe_id, tags)
    conn.close()
    typer.echo(json.dumps({"recipe_id": recipe_id, "added": tags}))


@app.command("remove")
def remove(recipe_id: int, tag: str):
    """Remove a tag from a recipe."""
    conn = get_db()
    remove_tag(conn, recipe_id, tag)
    conn.close()
    typer.echo(json.dumps({"recipe_id": recipe_id, "removed": tag}))


@app.command("list")
def list_cmd():
    """List all tags with counts."""
    conn = get_db()
    tags = list_tags(conn)
    conn.close()
    typer.echo(json.dumps(tags, default=str))
```

Update `src/grecipe/cli/main.py`:

```python
# src/grecipe/cli/main.py
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_cli/ -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/grecipe/cli/ tests/test_cli/
git commit -m "feat: recipe and tag CLI commands with JSON I/O and chat logging"
```

---

## Task 10: CLI Commands — Plan, Grocery, Chat, Display

**Files:**
- Create: `src/grecipe/cli/plan.py`
- Create: `src/grecipe/cli/grocery.py`
- Create: `src/grecipe/cli/chat.py`
- Create: `src/grecipe/cli/display.py`
- Modify: `src/grecipe/cli/main.py`
- Create: `tests/test_cli/test_plan_cli.py`
- Create: `tests/test_cli/test_grocery_cli.py`
- Create: `tests/test_cli/test_chat_cli.py`
- Create: `tests/test_cli/test_display_cli.py`

- [ ] **Step 1: Write failing tests for plan CLI**

```python
# tests/test_cli/test_plan_cli.py
import json
from typer.testing import CliRunner
from grecipe.cli.main import app

runner = CliRunner()


def test_plan_create_and_view(tmp_path, monkeypatch):
    monkeypatch.setenv("GRECIPE_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])

    result = runner.invoke(app, ["plan", "create", "--name", "This Week"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["id"] == 1

    result = runner.invoke(app, ["plan", "view", "1"])
    assert result.exit_code == 0


def test_plan_add_item(tmp_path, monkeypatch):
    monkeypatch.setenv("GRECIPE_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    runner.invoke(app, ["recipe", "add", "--json", json.dumps({"title": "Tacos", "source_type": "text"})])
    runner.invoke(app, ["plan", "create", "--name", "Week"])

    result = runner.invoke(app, ["plan", "add", "1", "1", "--date", "2026-03-20", "--meal", "dinner"])
    assert result.exit_code == 0
```

- [ ] **Step 2: Write failing tests for grocery CLI**

```python
# tests/test_cli/test_grocery_cli.py
import json
from typer.testing import CliRunner
from grecipe.cli.main import app

runner = CliRunner()


def test_grocery_create_standalone(tmp_path, monkeypatch):
    monkeypatch.setenv("GRECIPE_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])

    result = runner.invoke(app, ["grocery", "create", "--name", "Quick run"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["id"] == 1


def test_grocery_add_item_and_view(tmp_path, monkeypatch):
    monkeypatch.setenv("GRECIPE_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    runner.invoke(app, ["grocery", "create", "--name", "Test"])

    runner.invoke(app, ["grocery", "add-item", "1", "--name", "milk", "--quantity", "1", "--unit", "gallon"])
    result = runner.invoke(app, ["grocery", "view", "1"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data["items"]) == 1
```

- [ ] **Step 3: Write failing tests for chat CLI**

```python
# tests/test_cli/test_chat_cli.py
import json
from typer.testing import CliRunner
from grecipe.cli.main import app

runner = CliRunner()


def test_chat_log_and_search(tmp_path, monkeypatch):
    monkeypatch.setenv("GRECIPE_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])

    result = runner.invoke(app, [
        "chat", "log",
        "--action", "add_recipe",
        "--entity-type", "recipe",
        "--entity-id", "1",
        "--user-message", "add my taco recipe",
        "--assistant-response", "Added Tacos",
    ])
    assert result.exit_code == 0

    result = runner.invoke(app, ["chat", "search", "taco"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) == 1
```

- [ ] **Step 4: Write failing test for display CLI**

```python
# tests/test_cli/test_display_cli.py
import json
from typer.testing import CliRunner
from grecipe.cli.main import app

runner = CliRunner()


def test_display_render_recipe(tmp_path, monkeypatch):
    monkeypatch.setenv("GRECIPE_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    runner.invoke(app, ["recipe", "add", "--json", json.dumps({
        "title": "Pasta", "source_type": "text",
        "ingredients": [{"name": "pasta", "quantity": 8, "unit": "oz"}],
        "instructions": ["Boil", "Eat"],
    })])

    result = runner.invoke(app, ["display", "render", "--recipe-id", "1"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "path" in data
```

- [ ] **Step 5: Run tests to verify they fail**

```bash
pytest tests/test_cli/ -v
```

Expected: FAIL for new tests.

- [ ] **Step 6: Implement plan, grocery, chat, and display CLI commands**

```python
# src/grecipe/cli/plan.py
"""Meal plan CLI commands."""

import json
from typing import Optional

import typer

from grecipe.db.connection import get_db
from grecipe.models.plan import (
    create_plan, get_plan, edit_plan, delete_plan,
    add_plan_item, remove_plan_item, get_plan_items,
    list_plans, suggest_recipes,
)

app = typer.Typer(help="Meal plan management.")


def _output(data):
    typer.echo(json.dumps(data, default=str))


@app.command("create")
def create(
    name: str = typer.Option(..., "--name"),
    start_date: Optional[str] = typer.Option(None, "--start"),
    end_date: Optional[str] = typer.Option(None, "--end"),
):
    """Create a new meal plan."""
    conn = get_db()
    pid = create_plan(conn, name=name, start_date=start_date, end_date=end_date)
    conn.close()
    _output({"id": pid, "status": "created"})


@app.command("view")
def view(plan_id: int):
    """View a meal plan with its items."""
    conn = get_db()
    plan = get_plan(conn, plan_id)
    items = get_plan_items(conn, plan_id)
    conn.close()
    if plan:
        result = dict(plan)
        result["items"] = items
        _output(result)
    else:
        _output({"error": f"Plan {plan_id} not found"})
        raise typer.Exit(1)


@app.command("add")
def add(
    plan_id: int,
    recipe_id: int,
    date: str = typer.Option(..., "--date"),
    meal: str = typer.Option(..., "--meal"),
    servings: Optional[int] = typer.Option(None, "--servings"),
):
    """Add a recipe to a meal plan."""
    conn = get_db()
    item_id = add_plan_item(conn, plan_id, recipe_id, date=date,
                            meal_category=meal, servings_override=servings)
    conn.close()
    _output({"item_id": item_id, "status": "added"})


@app.command("remove")
def remove(plan_id: int, item_id: int):
    """Remove an item from a meal plan."""
    conn = get_db()
    remove_plan_item(conn, plan_id, item_id)
    conn.close()
    _output({"item_id": item_id, "status": "removed"})


@app.command("edit")
def edit_cmd(
    plan_id: int,
    name: Optional[str] = typer.Option(None, "--name"),
    start_date: Optional[str] = typer.Option(None, "--start"),
    end_date: Optional[str] = typer.Option(None, "--end"),
):
    """Edit a meal plan's metadata."""
    conn = get_db()
    edit_plan(conn, plan_id, name=name, start_date=start_date, end_date=end_date)
    conn.close()
    _output({"id": plan_id, "status": "updated"})


@app.command("delete")
def delete(plan_id: int):
    """Delete a meal plan."""
    conn = get_db()
    delete_plan(conn, plan_id)
    conn.close()
    _output({"id": plan_id, "status": "deleted"})


@app.command("suggest")
def suggest(limit: int = typer.Option(10, "--limit")):
    """Suggest recipes not recently planned."""
    conn = get_db()
    results = suggest_recipes(conn, limit=limit)
    conn.close()
    _output(results)


@app.command("list")
def list_cmd():
    """List all meal plans."""
    conn = get_db()
    plans = list_plans(conn)
    conn.close()
    _output(plans)
```

```python
# src/grecipe/cli/grocery.py
"""Grocery list CLI commands."""

import json
from typing import Optional

import typer

from grecipe.db.connection import get_db
from grecipe.models.grocery import (
    create_list, get_list, delete_list, list_lists,
    add_item, check_item, get_items, export_list,
    generate_from_plan,
)

app = typer.Typer(help="Grocery list management.")


def _output(data):
    typer.echo(json.dumps(data, default=str))


@app.command("create")
def create(name: str = typer.Option(..., "--name")):
    """Create a standalone grocery list."""
    conn = get_db()
    lid = create_list(conn, name=name)
    conn.close()
    _output({"id": lid, "status": "created"})


@app.command("generate")
def generate(
    plan_id: int,
    servings_multiplier: float = typer.Option(1.0, "--servings-multiplier"),
):
    """Generate a grocery list from a meal plan."""
    conn = get_db()
    lid = generate_from_plan(conn, plan_id, servings_multiplier=servings_multiplier)
    items = get_items(conn, lid)
    conn.close()
    _output({"id": lid, "item_count": len(items), "status": "generated"})


@app.command("view")
def view(list_id: int):
    """View a grocery list grouped by section."""
    conn = get_db()
    gl = get_list(conn, list_id)
    items = get_items(conn, list_id)
    conn.close()
    if gl:
        result = dict(gl)
        result["items"] = items
        _output(result)
    else:
        _output({"error": f"List {list_id} not found"})
        raise typer.Exit(1)


@app.command("add-item")
def add_item_cmd(
    list_id: int,
    name: str = typer.Option(..., "--name"),
    quantity: Optional[float] = typer.Option(None, "--quantity"),
    unit: Optional[str] = typer.Option(None, "--unit"),
    section: Optional[str] = typer.Option(None, "--section"),
):
    """Add an item to a grocery list."""
    conn = get_db()
    iid = add_item(conn, list_id, name=name, quantity=quantity, unit=unit, store_section=section)
    conn.close()
    _output({"item_id": iid, "status": "added"})


@app.command("check")
def check(list_id: int, item_id: int):
    """Mark a grocery item as checked."""
    conn = get_db()
    check_item(conn, list_id, item_id)
    conn.close()
    _output({"item_id": item_id, "status": "checked"})


@app.command("delete")
def delete(list_id: int):
    """Delete a grocery list."""
    conn = get_db()
    delete_list(conn, list_id)
    conn.close()
    _output({"id": list_id, "status": "deleted"})


@app.command("list")
def list_cmd():
    """List all grocery lists."""
    conn = get_db()
    lists = list_lists(conn)
    conn.close()
    _output(lists)


@app.command("export")
def export(list_id: int):
    """Export a grocery list as plain text."""
    conn = get_db()
    text = export_list(conn, list_id)
    conn.close()
    typer.echo(text)
```

```python
# src/grecipe/cli/chat.py
"""Chat log CLI commands."""

import json
from typing import Optional

import typer

from grecipe.db.connection import get_db
from grecipe.models.chat import log_chat, search_chat

app = typer.Typer(help="Chat log management.")


@app.command("log")
def log(
    action: str = typer.Option(..., "--action"),
    entity_type: Optional[str] = typer.Option(None, "--entity-type"),
    entity_id: Optional[int] = typer.Option(None, "--entity-id"),
    user_message: Optional[str] = typer.Option(None, "--user-message"),
    assistant_response: Optional[str] = typer.Option(None, "--assistant-response"),
):
    """Log a chat interaction."""
    conn = get_db()
    log_id = log_chat(conn, user_message=user_message, assistant_response=assistant_response,
                      action_type=action, entity_type=entity_type, entity_id=entity_id)
    conn.close()
    typer.echo(json.dumps({"id": log_id, "status": "logged"}))


@app.command("search")
def search(query: str):
    """Search chat history."""
    conn = get_db()
    results = search_chat(conn, query)
    conn.close()
    typer.echo(json.dumps(results, default=str))
```

```python
# src/grecipe/cli/display.py
"""Display rendering CLI commands."""

import json
from pathlib import Path
from typing import Optional

import typer

from grecipe.db.connection import get_db, get_db_path

app = typer.Typer(help="Visual rendering.")


@app.command("render")
def render(
    recipe_id: Optional[int] = typer.Option(None, "--recipe-id"),
    plan_id: Optional[int] = typer.Option(None, "--plan-id"),
    grocery_id: Optional[int] = typer.Option(None, "--grocery-id"),
):
    """Render a recipe, plan, or grocery list to HTML."""
    conn = get_db()
    output_dir = get_db_path().parent / "output"

    if recipe_id:
        from grecipe.display.renderer import render_recipe
        path = render_recipe(conn, recipe_id, output_dir)
    elif plan_id:
        from grecipe.display.renderer import render_plan
        path = render_plan(conn, plan_id, output_dir)
    elif grocery_id:
        from grecipe.display.renderer import render_grocery
        path = render_grocery(conn, grocery_id, output_dir)
    else:
        typer.echo(json.dumps({"error": "Provide --recipe-id, --plan-id, or --grocery-id"}))
        raise typer.Exit(1)

    conn.close()
    typer.echo(json.dumps({"path": str(path), "status": "rendered"}))
```

Update `src/grecipe/cli/main.py` to register all subcommands:

```python
# src/grecipe/cli/main.py
"""grecipe CLI entry point."""

import typer

app = typer.Typer(name="grecipe", help="Recipe management for Claude Cowork.")


def register_subcommands():
    from grecipe.cli.db_cmd import app as db_app
    from grecipe.cli.recipe import app as recipe_app
    from grecipe.cli.tag import app as tag_app
    from grecipe.cli.plan import app as plan_app
    from grecipe.cli.grocery import app as grocery_app
    from grecipe.cli.chat import app as chat_app
    from grecipe.cli.display import app as display_app
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
```

- [ ] **Step 7: Run all tests**

```bash
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add src/grecipe/cli/ tests/test_cli/
git commit -m "feat: plan, grocery, chat, and display CLI commands"
```

---

## Task 11: Claude Skill File (CLAUDE.md)

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: Write the skill file**

```markdown
# grecipe — Recipe Assistant

You are a friendly, knowledgeable recipe assistant. Help manage recipes, plan meals, and create grocery lists using the `grecipe` CLI.

## Setup

Before first use, initialize the database:
```bash
grecipe db init
```

## Available Commands

### Adding Recipes

**From conversation (primary method):** Parse the user's recipe text into structured JSON, then:
```bash
grecipe recipe add --json '{"title": "Lemon Chicken", "description": "Roasted chicken with lemon", "source_type": "text", "servings": 4, "ingredients": [{"name": "chicken breast", "quantity": 2, "unit": "lbs"}, {"name": "lemon", "quantity": 2, "unit": "whole"}], "instructions": ["Preheat oven to 400F", "Season chicken with salt and pepper", "Roast for 25 minutes"], "notes": ""}' --log-user-msg "add my lemon chicken recipe" --log-assistant-msg "Added Lemon Chicken (id=1)"
```

**From URL:**
```bash
grecipe recipe import-url "https://example.com/recipe" --log-user-msg "save this recipe" --log-assistant-msg "Imported recipe from URL"
```

### Viewing & Searching

```bash
grecipe recipe view <id>
grecipe recipe list [--tag mexican] [--category dinner] [--favorite] [--sort rating|date|title] [--limit 10] [--offset 0]
grecipe recipe search "chicken lemon"
```

### Editing Recipes

Use merge-patch — only include fields to change:
```bash
grecipe recipe edit <id> --json '{"title": "Updated Title", "servings": 6}' --log-user-msg "..." --log-assistant-msg "..."
```

### Tags & Categories

```bash
grecipe tag add <recipe_id> "mexican" "quick" "weeknight"
grecipe tag remove <recipe_id> "quick"
grecipe tag list
grecipe recipe set-dietary <recipe_id> "gluten-free" "dairy-free"
```

### Rating & Favorites

```bash
grecipe recipe rate <id> --rating 5
grecipe recipe favorite <id>
```

### Meal Planning

```bash
grecipe plan create --name "This Week" [--start 2026-03-20] [--end 2026-03-26]
grecipe plan add <plan_id> <recipe_id> --date 2026-03-20 --meal dinner
grecipe plan view <plan_id>
grecipe plan suggest --limit 10
grecipe plan list
grecipe plan edit <plan_id> --name "New Name"
grecipe plan delete <plan_id>
```

### Grocery Lists

```bash
grecipe grocery generate <plan_id> [--servings-multiplier 2]
grecipe grocery create --name "Quick run"
grecipe grocery add-item <list_id> --name "milk" --quantity 1 --unit gallon --section dairy
grecipe grocery view <list_id>
grecipe grocery check <list_id> <item_id>
grecipe grocery export <list_id>
grecipe grocery list
grecipe grocery delete <list_id>
```

### Visual Display

Generate HTML with dish photos when the user is browsing recipes or reviewing meal plans:
```bash
grecipe display render --recipe-id <id>
grecipe display render --plan-id <id>
grecipe display render --grocery-id <id>
```

### Chat History

```bash
grecipe chat log --action "add_recipe" --entity-type "recipe" --entity-id 1 --user-message "..." --assistant-response "..."
grecipe chat search "taco recipe modification"
```

### Database Info

```bash
grecipe db stats
```

## Behavior Guidelines

1. **Always log interactions.** Use `--log-user-msg` and `--log-assistant-msg` on data-modifying commands. For non-modifying interactions, use `grecipe chat log`.

2. **Parse recipes carefully.** When the user pastes recipe text, extract: title, description, ingredients (with quantity + unit + name), instructions (as ordered steps), servings, prep/cook time. Ask for clarification if the text is ambiguous.

3. **Show visuals for browsing.** When the user is choosing between recipes, reviewing a meal plan, or looking at a grocery list, use `grecipe display render` to generate an HTML page with photos.

4. **Be smart about meal planning.** Use `grecipe plan suggest` to recommend recipes that haven't been used recently. Consider dietary flags and meal categories when suggesting.

5. **Grocery list intelligence.** The CLI handles unit normalization and store section grouping automatically. Just generate from the plan.

6. **Tag generously.** When adding recipes, suggest relevant tags based on the content (cuisine, cooking method, dietary properties, occasion).

7. **Note the source.** When importing from a URL, the source is tracked automatically. For pasted recipes, ask where it came from if relevant.

## All output is JSON by default. Parse the JSON to present results conversationally.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "feat: Claude skill file for Cowork integration"
```

---

## Task 12: Integration Test & Final Verification

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write an end-to-end integration test**

```python
# tests/test_integration.py
"""End-to-end test simulating a typical Claude Cowork session."""

import json


def test_full_workflow(db, tmp_path):
    """Simulate: add recipes → tag → plan meals → generate grocery list → render."""
    from grecipe.models.recipe import add_recipe, get_recipe
    from grecipe.models.tag import add_tags
    from grecipe.models.meal_category import set_categories
    from grecipe.models.dietary import set_dietary
    from grecipe.models.plan import create_plan, add_plan_item, get_plan_items
    from grecipe.models.grocery import generate_from_plan, get_items, export_list
    from grecipe.models.chat import log_chat, search_chat
    from grecipe.display.renderer import render_recipe, render_plan

    # 1. Add recipes
    r1 = add_recipe(db, {
        "title": "Lemon Chicken",
        "source_type": "text",
        "servings": 4,
        "ingredients": json.dumps([
            {"name": "chicken breast", "quantity": 2, "unit": "pound"},
            {"name": "lemon", "quantity": 2, "unit": "whole"},
            {"name": "olive oil", "quantity": 2, "unit": "tablespoon"},
        ]),
        "instructions": json.dumps(["Preheat oven to 400F", "Season and roast"]),
    })
    r2 = add_recipe(db, {
        "title": "Caesar Salad",
        "source_type": "text",
        "servings": 2,
        "ingredients": json.dumps([
            {"name": "lettuce", "quantity": 1, "unit": "head"},
            {"name": "parmesan", "quantity": 0.5, "unit": "cup"},
            {"name": "olive oil", "quantity": 1, "unit": "tablespoon"},
        ]),
        "instructions": json.dumps(["Chop lettuce", "Toss with dressing"]),
    })

    # 2. Tag and categorize
    add_tags(db, r1, ["weeknight", "healthy"])
    add_tags(db, r2, ["quick", "healthy"])
    set_categories(db, r1, ["dinner"])
    set_categories(db, r2, ["lunch", "side"])
    set_dietary(db, r2, ["gluten-free"])

    # 3. Log interactions
    log_chat(db, user_message="add my lemon chicken recipe",
             assistant_response="Added Lemon Chicken (id=1)",
             action_type="add_recipe", entity_type="recipe", entity_id=r1)

    # 4. Create meal plan
    pid = create_plan(db, name="This Week", start_date="2026-03-20", end_date="2026-03-26")
    add_plan_item(db, pid, r1, date="2026-03-20", meal_category="dinner")
    add_plan_item(db, pid, r2, date="2026-03-20", meal_category="lunch")
    items = get_plan_items(db, pid)
    assert len(items) == 2

    # 5. Generate grocery list
    lid = generate_from_plan(db, pid)
    grocery_items = get_items(db, lid)
    names = {i["name"] for i in grocery_items}
    assert "chicken breast" in names
    assert "olive oil" in names  # aggregated from both recipes

    # 6. Export grocery list
    text = export_list(db, lid)
    assert "chicken breast" in text

    # 7. Search chat history
    results = search_chat(db, "lemon chicken")
    assert len(results) == 1

    # 8. Render HTML
    recipe_html = render_recipe(db, r1, output_dir=tmp_path / "output")
    assert recipe_html.exists()
    assert "Lemon Chicken" in recipe_html.read_text()

    plan_html = render_plan(db, pid, output_dir=tmp_path / "output")
    assert plan_html.exists()
    assert "This Week" in plan_html.read_text()
```

- [ ] **Step 2: Run all tests**

```bash
pytest tests/ -v --tb=short
```

Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: end-to-end integration test covering full workflow"
```

- [ ] **Step 4: Run final check**

```bash
grecipe db init
grecipe db stats
grecipe recipe add --json '{"title": "Test Recipe", "source_type": "text", "servings": 2}'
grecipe recipe list
```

Expected: CLI works end-to-end with JSON output.

---

## Review Findings & Amendments

The following amendments address issues found during plan review. Apply these during the relevant tasks. **Amendments take precedence over the code blocks in the tasks above.** When an amendment modifies a command, update the code block accordingly during implementation.

### Finding-to-Amendment Traceability

| # | Finding | Amendment |
|---|---------|-----------|
| 1 | `--format text` not supported | Amendment 3 |
| 2 | `recipe search` uses LIKE, not FTS5 | Amendment 2 |
| 3 | `recipe add --title` convenience flags incomplete | Accepted as-is; `--json` is the primary path for Claude. Minimal convenience flags are sufficient. |
| 4 | `plan suggest` takes no `plan_id` | Amendment 5 |
| 5 | `display render` uses options instead of positional args | Accepted as-is; options (`--recipe-id`, `--plan-id`, `--grocery-id`) are clearer than an ambiguous positional arg. CLAUDE.md already documents the option-based interface. |
| 6 | `--log-user-msg` / `--log-assistant-msg` missing from most commands | Amendment 1 |
| 7 | Missing CLI tests for `grocery list`, `grocery export`, `grocery delete` | Amendment 4 (expanded) |
| 8 | Missing `test_db_cli.py` | Amendment 4 |

### Amendment 1: Add `--log-user-msg` / `--log-assistant-msg` to ALL data-modifying CLI commands

Per the spec: "All data-modifying commands accept optional `--log-user-msg` and `--log-assistant-msg` flags."

During Tasks 9 and 10, add these optional flags to every data-modifying command:
- `tag add`, `tag remove`
- `recipe set-dietary`, `recipe rate`, `recipe favorite`
- `plan create`, `plan add`, `plan remove`, `plan edit`, `plan delete`
- `grocery create`, `grocery generate`, `grocery add-item`, `grocery check`, `grocery delete`

Pattern — add these two parameters to each function, plus a log call before `conn.close()`:

```python
log_user_msg: Optional[str] = typer.Option(None, "--log-user-msg"),
log_assistant_msg: Optional[str] = typer.Option(None, "--log-assistant-msg"),
```

```python
if log_user_msg or log_assistant_msg:
    log_chat(conn, user_message=log_user_msg, assistant_response=log_assistant_msg,
             action_type="<action>", entity_type="<type>", entity_id=<id>)
```

**Checklist of commands to modify (action_type / entity_type for each):**

- [ ] `tag add` → `add_tag` / `recipe`
- [ ] `tag remove` → `remove_tag` / `recipe`
- [ ] `recipe set-dietary` → `set_dietary` / `recipe`
- [ ] `recipe rate` → `rate_recipe` / `recipe`
- [ ] `recipe favorite` → `favorite_recipe` / `recipe`
- [ ] `plan create` → `create_plan` / `plan`
- [ ] `plan add` → `add_plan_item` / `plan`
- [ ] `plan remove` → `remove_plan_item` / `plan`
- [ ] `plan edit` → `edit_plan` / `plan`
- [ ] `plan delete` → `delete_plan` / `plan`
- [ ] `grocery create` → `create_list` / `grocery_list`
- [ ] `grocery generate` → `generate_list` / `grocery_list`
- [ ] `grocery add-item` → `add_grocery_item` / `grocery_list`
- [ ] `grocery check` → `check_item` / `grocery_list`
- [ ] `grocery delete` → `delete_list` / `grocery_list`

### Amendment 2: Recipe search — document FTS5 as future enhancement

The `search_recipes` function in Task 2 uses LIKE queries as a pragmatic starting point. This is a known simplification. To fully match the spec, a `recipes_fts` FTS5 virtual table should be added (mirroring the `chat_log_fts` pattern). This can be added as a follow-up task without changing the CLI interface.

Additionally, recipe search should also join through `recipe_tags`/`tags` to search tag names, as the spec says "FTS across titles, ingredients, tags."

### Amendment 3: Add `--format text` support

Add a global `--format` option to the top-level Typer app in `main.py`:

```python
format_option: str = typer.Option("json", "--format", help="Output format: json or text")
```

For V1, `text` format can simply pretty-print the JSON. This satisfies the spec without building a full text formatter for every command.

### Amendment 4: Missing test files and CLI test coverage

During Task 9, also create:
- `tests/test_cli/__init__.py` (empty)
- `tests/test_cli/test_db_cli.py` with basic tests for `db init` and `db stats`

During Task 10, add CLI tests for:
- `grocery list` (list all grocery lists)
- `grocery export` (export as text)
- `grocery delete` (delete a list)
- `plan delete` and `plan edit`

### Amendment 5: `plan suggest` should accept optional `--plan-id`

Update the `suggest` command in Task 10 to accept an optional `--plan-id` flag. When provided, exclude recipes already in that plan from suggestions.

### Amendment 6: Grocery aggregation edge case

In Task 6, the `generate_from_plan` function's aggregation logic should handle incompatible units by keeping them as separate line items rather than naively summing. Update the final `else` branch:

```python
else:
    # Incompatible units — add as separate item
    alt_key = f"{name} ({unit})"
    aggregated[alt_key] = {
        "quantity": qty,
        "unit": unit,
        "source_recipes": {item["rid"]},
    }
```
