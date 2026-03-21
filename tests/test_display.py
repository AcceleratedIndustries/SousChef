"""Tests for HTML display renderer."""
import json
import pytest

from grecipe.models.recipe import add_recipe
from grecipe.models.plan import create_plan, add_plan_item
from grecipe.models.grocery import create_list, add_item
from grecipe.display.renderer import render_recipe, render_plan, render_grocery


def test_render_recipe(db, tmp_path):
    """Render a recipe to HTML and verify file exists with expected content."""
    recipe_id = add_recipe(db, {
        "title": "Spaghetti Carbonara",
        "description": "Classic Italian pasta dish",
        "ingredients": json.dumps([
            {"name": "pasta", "quantity": 200, "unit": "g"},
            {"name": "eggs", "quantity": 2, "unit": None},
            {"name": "parmesan", "quantity": 50, "unit": "g"},
        ]),
        "instructions": json.dumps([
            "Boil water and cook pasta",
            "Mix eggs and cheese",
            "Combine pasta with egg mixture",
        ]),
        "servings": 2,
        "prep_time_minutes": 10,
        "cook_time_minutes": 20,
        "rating": 5,
    })

    output_path = render_recipe(db, recipe_id, tmp_path)

    assert output_path.exists()
    content = output_path.read_text()
    assert "Spaghetti Carbonara" in content
    assert "pasta" in content


def test_render_plan(db, tmp_path):
    """Render a meal plan to HTML and verify file exists with expected content."""
    recipe_id = add_recipe(db, {
        "title": "Grilled Chicken",
        "ingredients": json.dumps([{"name": "chicken", "quantity": 1, "unit": "lb"}]),
        "instructions": json.dumps(["Grill the chicken"]),
    })

    plan_id = create_plan(db, "Weekly Meal Plan", start_date="2026-03-21", end_date="2026-03-27")
    add_plan_item(db, plan_id, recipe_id, date="2026-03-21", meal_category="dinner")

    output_path = render_plan(db, plan_id, tmp_path)

    assert output_path.exists()
    content = output_path.read_text()
    assert "Weekly Meal Plan" in content
    assert "Grilled Chicken" in content


def test_render_grocery(db, tmp_path):
    """Render a grocery list to HTML and verify file exists with expected content."""
    list_id = create_list(db, "My Weekly Groceries")
    add_item(db, list_id, "milk", quantity=1, unit="gallon", store_section="dairy")

    output_path = render_grocery(db, list_id, tmp_path)

    assert output_path.exists()
    content = output_path.read_text()
    assert "My Weekly Groceries" in content
    assert "milk" in content
