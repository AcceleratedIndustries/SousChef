"""Tests for the recipe history model."""
import pytest
from grecipe.models.recipe import add_recipe, get_recipe
from grecipe.models.history import record_change, get_history


def test_record_history_on_edit(db):
    """Record a change to a recipe and verify history entry is stored."""
    recipe_id = add_recipe(db, {"title": "Soup"})
    old_recipe = get_recipe(db, recipe_id)

    changes = {"title": "Tomato Soup"}
    record_change(db, recipe_id, changes, old_recipe)

    history = get_history(db, recipe_id)
    assert len(history) == 1
    entry = history[0]
    assert "title" in entry["changed_fields"]
    assert entry["previous_values"]["title"] == "Soup"
