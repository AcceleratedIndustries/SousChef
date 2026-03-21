"""Tests for tag, dietary, and meal category models."""
import pytest

from souschef.models.recipe import add_recipe
from souschef.models.tag import add_tags, remove_tag, get_tags_for_recipe, list_tags
from souschef.models.dietary import set_dietary, get_dietary
from souschef.models.meal_category import set_categories, get_categories


SAMPLE_RECIPE = {"title": "Test Recipe"}


def test_add_tags_to_recipe(db):
    recipe_id = add_recipe(db, SAMPLE_RECIPE)
    add_tags(db, recipe_id, ["mexican", "quick"])
    tags = get_tags_for_recipe(db, recipe_id)
    assert "mexican" in tags
    assert "quick" in tags


def test_remove_tag_from_recipe(db):
    recipe_id = add_recipe(db, SAMPLE_RECIPE)
    add_tags(db, recipe_id, ["mexican", "quick"])
    remove_tag(db, recipe_id, "mexican")
    tags = get_tags_for_recipe(db, recipe_id)
    assert "mexican" not in tags
    assert "quick" in tags


def test_list_all_tags(db):
    recipe1 = add_recipe(db, {"title": "Recipe One"})
    recipe2 = add_recipe(db, {"title": "Recipe Two"})
    add_tags(db, recipe1, ["quick", "mexican"])
    add_tags(db, recipe2, ["quick", "vegetarian"])

    tags = list_tags(db)
    tag_map = {t["name"]: t["count"] for t in tags}
    assert tag_map["quick"] == 2
    assert tag_map["mexican"] == 1
    assert tag_map["vegetarian"] == 1
    # ordered by count DESC: "quick" should be first
    assert tags[0]["name"] == "quick"


def test_set_dietary_flags(db):
    recipe_id = add_recipe(db, SAMPLE_RECIPE)
    set_dietary(db, recipe_id, ["gluten-free", "vegan"])
    flags = get_dietary(db, recipe_id)
    assert "gluten-free" in flags
    assert "vegan" in flags


def test_set_meal_categories(db):
    recipe_id = add_recipe(db, SAMPLE_RECIPE)
    set_categories(db, recipe_id, ["breakfast", "brunch"])
    categories = get_categories(db, recipe_id)
    assert "breakfast" in categories
    assert "brunch" in categories
