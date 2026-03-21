"""Tests for code quality fixes: row_factory preservation, search limit,
delete-nonexistent, rate/favorite-nonexistent."""
import sqlite3
import pytest

from souschef.models.recipe import (
    add_recipe,
    get_recipe,
    list_recipes,
    search_recipes,
    delete_recipe,
    rate_recipe,
    favorite_recipe,
)
from souschef.models.plan import (
    create_plan,
    delete_plan,
    remove_plan_item,
    add_plan_item,
)
from souschef.models.grocery import (
    create_list,
    delete_list,
)

SAMPLE = {"title": "Test Recipe", "source_type": "text"}


# --- Issue 4: row_factory preserved after model calls ---

class TestRowFactoryPreserved:
    def test_row_factory_preserved_after_recipe_calls(self, db):
        """Verify model calls don't corrupt the connection's row_factory."""
        original_factory = db.row_factory
        add_recipe(db, {"title": "Test", "source_type": "text"})
        get_recipe(db, 1)
        list_recipes(db)
        assert db.row_factory == original_factory

    def test_row_factory_preserved_after_search(self, db):
        add_recipe(db, SAMPLE)
        original_factory = db.row_factory
        search_recipes(db, "Test")
        assert db.row_factory == original_factory

    def test_row_factory_is_sqlite3_row(self, db):
        """Connection should use sqlite3.Row, not None or dict_row_factory."""
        assert db.row_factory == sqlite3.Row
        add_recipe(db, SAMPLE)
        get_recipe(db, 1)
        assert db.row_factory == sqlite3.Row


# --- Issue 6: search_recipes limit ---

class TestSearchLimit:
    def test_search_respects_limit(self, db):
        for i in range(10):
            add_recipe(db, {"title": f"Apple Pie {i}", "source_type": "text"})
        results = search_recipes(db, "Apple", limit=3)
        assert len(results) == 3

    def test_search_default_limit(self, db):
        """Default limit should be 100 (not unlimited)."""
        for i in range(5):
            add_recipe(db, {"title": f"Banana Bread {i}", "source_type": "text"})
        results = search_recipes(db, "Banana")
        assert len(results) == 5  # all 5 under the 100 default


# --- Issue 7: delete nonexistent IDs ---

class TestDeleteNonexistent:
    def test_delete_recipe_nonexistent(self, db):
        result = delete_recipe(db, 99999)
        assert result is False

    def test_delete_recipe_existing(self, db):
        rid = add_recipe(db, SAMPLE)
        result = delete_recipe(db, rid)
        assert result is True

    def test_delete_plan_nonexistent(self, db):
        result = delete_plan(db, 99999)
        assert result is False

    def test_delete_plan_existing(self, db):
        pid = create_plan(db, "Test Plan")
        result = delete_plan(db, pid)
        assert result is True

    def test_delete_list_nonexistent(self, db):
        result = delete_list(db, 99999)
        assert result is False

    def test_delete_list_existing(self, db):
        lid = create_list(db, "Test List")
        result = delete_list(db, lid)
        assert result is True

    def test_remove_plan_item_nonexistent(self, db):
        pid = create_plan(db, "Test Plan")
        result = remove_plan_item(db, pid, 99999)
        assert result is False

    def test_remove_plan_item_existing(self, db):
        rid = add_recipe(db, SAMPLE)
        pid = create_plan(db, "Test Plan")
        item_id = add_plan_item(db, pid, rid, "2026-03-25", "dinner")
        result = remove_plan_item(db, pid, item_id)
        assert result is True


# --- Issue 8: rate/favorite nonexistent recipes ---

class TestRateFavoriteNonexistent:
    def test_rate_nonexistent_recipe(self, db):
        with pytest.raises(ValueError, match="not found"):
            rate_recipe(db, 99999, 3)

    def test_rate_existing_recipe(self, db):
        rid = add_recipe(db, SAMPLE)
        rate_recipe(db, rid, 4)  # should not raise
        recipe = get_recipe(db, rid)
        assert recipe["rating"] == 4

    def test_favorite_nonexistent_recipe(self, db):
        with pytest.raises(ValueError, match="not found"):
            favorite_recipe(db, 99999, True)

    def test_favorite_existing_recipe(self, db):
        rid = add_recipe(db, SAMPLE)
        favorite_recipe(db, rid, True)  # should not raise
        recipe = get_recipe(db, rid)
        assert recipe["is_favorite"] in (1, True)
