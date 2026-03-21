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
