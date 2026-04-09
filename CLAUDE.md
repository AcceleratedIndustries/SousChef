# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Development

```bash
pip install -e ".[dev]"       # Install with dev dependencies
souschef db init              # Initialize SQLite database (~/.souschef/souschef.db)
```

## Testing

```bash
pytest                             # Run all tests
pytest tests/test_recipe_model.py  # Run a single test file
pytest -k "test_add"               # Run tests matching a name pattern
pytest --cov=souschef              # Run with coverage
```

Tests use a fresh SQLite database per test via the `db` fixture in `tests/conftest.py` (creates a temp DB, runs schema init + seed, yields the connection). CLI tests are in `tests/test_cli/` and use Typer's `CliRunner`.

## Architecture

**Typer CLI application** backed by **SQLite** (WAL mode, foreign keys enforced). Database lives at `~/.souschef/souschef.db` by default, overridable via `SOUSCHEF_DB_DIR` env var. Claude is the only UI — there is no standalone GUI.

### Layer structure

- **`cli/`** — Typer subcommand groups (`recipe`, `tag`, `plan`, `grocery`, `chat`, `display`, `update`, `db`). Each module defines a `typer.Typer()` app registered in `cli/main.py`. All commands output JSON. Data-modifying commands accept `--log-user-msg` / `--log-assistant-msg` to write to the chat_log table atomically.
- **`models/`** — Pure data-access functions (no CLI concerns). Each module operates on a `sqlite3.Connection` passed as the first argument. No global DB state.
- **`db/`** — Connection management (`connection.py`), schema DDL as a single SQL string (`schema.py`), and seed data (`seed.py`). The `dict_rows` context manager temporarily swaps the row factory to return plain dicts.
- **`display/`** — Jinja2 HTML renderer with templates for recipes, plans, and grocery lists. Output goes to files like `recipe_{id}.html`.
- **`scraper/`** — URL-based recipe import using `recipe-scrapers` + `httpx`. Downloads images with content-type detection.
- **`units.py`** — Unit normalization (alias mapping), volume/weight conversion tables, and store-section inference by keyword matching. Used by grocery generation to aggregate compatible ingredients.
- **`update.py`** — Self-update mechanism: discovers repo root from `__file__` path, runs git fetch/pull via subprocess, reinstalls with pip.

### Key patterns

- JSON fields (`ingredients`, `instructions`) are stored as JSON text in SQLite and encoded/decoded at the model layer.
- Chat history uses FTS5 virtual table (`chat_log_fts`) with triggers for automatic sync.
- `recipe_history` tracks field-level changes with previous values, linked to chat_log entries.
- Grocery generation normalizes units via `UNIT_ALIASES`, combines compatible volume/weight quantities, and falls back to separate line items (keyed as `"name (unit)"`) when units are incompatible.

## Design docs

Specs and implementation plans are in `docs/superpowers/`.
