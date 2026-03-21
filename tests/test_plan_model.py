"""Tests for the meal plan model."""
import pytest

from souschef.models.plan import (
    create_plan,
    get_plan,
    edit_plan,
    delete_plan,
    add_plan_item,
    remove_plan_item,
    get_plan_items,
    list_plans,
    suggest_recipes,
)
from souschef.models.recipe import add_recipe


SAMPLE_RECIPE = {
    "title": "Pasta Primavera",
    "description": "A light vegetable pasta.",
    "servings": 4,
}


def test_create_plan(db):
    plan_id = create_plan(db, "Week 1", start_date="2026-03-23", end_date="2026-03-29")
    assert isinstance(plan_id, int)
    assert plan_id > 0

    plan = get_plan(db, plan_id)
    assert plan is not None
    assert plan["name"] == "Week 1"
    assert plan["start_date"] == "2026-03-23"
    assert plan["end_date"] == "2026-03-29"


def test_add_item_to_plan(db):
    recipe_id = add_recipe(db, SAMPLE_RECIPE)
    plan_id = create_plan(db, "Test Plan")

    item_id = add_plan_item(db, plan_id, recipe_id, "2026-03-25", "dinner")
    assert isinstance(item_id, int)
    assert item_id > 0

    items = get_plan_items(db, plan_id)
    assert len(items) == 1
    item = items[0]
    assert item["recipe_id"] == recipe_id
    assert item["recipe_title"] == "Pasta Primavera"
    assert item["meal_category"] == "dinner"
    assert item["date"] == "2026-03-25"


def test_remove_plan_item(db):
    recipe_id = add_recipe(db, SAMPLE_RECIPE)
    plan_id = create_plan(db, "Test Plan")
    item_id = add_plan_item(db, plan_id, recipe_id, "2026-03-25", "lunch")

    remove_plan_item(db, plan_id, item_id)
    items = get_plan_items(db, plan_id)
    assert len(items) == 0


def test_delete_plan(db):
    plan_id = create_plan(db, "Temporary Plan")
    assert get_plan(db, plan_id) is not None

    delete_plan(db, plan_id)
    assert get_plan(db, plan_id) is None


def test_suggest_recipes(db):
    recipe1_id = add_recipe(db, {**SAMPLE_RECIPE, "title": "Planned Recipe", "rating": 3})
    recipe2_id = add_recipe(db, {**SAMPLE_RECIPE, "title": "Unplanned Recipe", "rating": 5})

    plan_id = create_plan(db, "Current Week")
    add_plan_item(db, plan_id, recipe1_id, "2026-03-24", "dinner")

    suggestions = suggest_recipes(db, limit=10)
    ids = [r["id"] for r in suggestions]

    assert recipe2_id in ids
    assert recipe1_id in ids
    # Unplanned recipe should come first (NULLS FIRST)
    assert ids.index(recipe2_id) < ids.index(recipe1_id)


def test_list_plans(db):
    id1 = create_plan(db, "Plan Alpha")
    id2 = create_plan(db, "Plan Beta")

    plans = list_plans(db)
    assert len(plans) == 2
    ids = [p["id"] for p in plans]
    assert id1 in ids
    assert id2 in ids
