"""Tests for the grocery model."""
import json
import pytest

from grecipe.models.grocery import (
    create_list,
    get_list,
    delete_list,
    list_lists,
    add_item,
    check_item,
    get_items,
    export_list,
    generate_from_plan,
)
from grecipe.models.recipe import add_recipe
from grecipe.models.plan import create_plan, add_plan_item


def test_create_standalone_list(db):
    list_id = create_list(db, "Weekly Groceries")
    assert isinstance(list_id, int)
    assert list_id > 0

    gl = get_list(db, list_id)
    assert gl is not None
    assert gl["name"] == "Weekly Groceries"
    assert gl["meal_plan_id"] is None


def test_add_item_to_list(db):
    list_id = create_list(db, "Test List")
    item_id = add_item(db, list_id, "milk", quantity=1.0, unit="gallon")
    assert isinstance(item_id, int)
    assert item_id > 0

    items = get_items(db, list_id)
    assert len(items) == 1
    assert items[0]["name"] == "milk"
    assert items[0]["quantity"] == 1.0
    assert items[0]["unit"] == "gallon"
    assert items[0]["store_section"] == "dairy"


def test_check_item(db):
    list_id = create_list(db, "Check Test")
    item_id = add_item(db, list_id, "eggs", quantity=12)

    check_item(db, list_id, item_id, checked=True)

    items = get_items(db, list_id)
    assert items[0]["is_checked"] == 1


def test_generate_from_plan(db):
    # Recipe 1: 2 tbsp olive oil
    recipe1_id = add_recipe(db, {
        "title": "Stir Fry",
        "servings": 2,
        "ingredients": json.dumps([
            {"name": "olive oil", "quantity": 2, "unit": "tbsp"},
            {"name": "chicken breast", "quantity": 200, "unit": "gram"},
        ]),
    })
    # Recipe 2: 1 tbsp olive oil
    recipe2_id = add_recipe(db, {
        "title": "Sauteed Veggies",
        "servings": 2,
        "ingredients": json.dumps([
            {"name": "olive oil", "quantity": 1, "unit": "tbsp"},
            {"name": "banana", "quantity": 2, "unit": None},
        ]),
    })

    plan_id = create_plan(db, "Test Week")
    add_plan_item(db, plan_id, recipe1_id, "2026-03-24", "dinner")
    add_plan_item(db, plan_id, recipe2_id, "2026-03-25", "dinner")

    grocery_list_id = generate_from_plan(db, plan_id)
    assert isinstance(grocery_list_id, int)

    items = get_items(db, grocery_list_id)
    names = {item["name"]: item for item in items}

    # Olive oil should be aggregated: 2 tbsp + 1 tbsp = 3 tablespoon
    assert "olive oil" in names
    oil = names["olive oil"]
    assert abs(oil["quantity"] - 3.0) < 1e-6
    assert oil["unit"] == "tablespoon"


def test_delete_list(db):
    list_id = create_list(db, "Temp List")
    assert get_list(db, list_id) is not None

    delete_list(db, list_id)
    assert get_list(db, list_id) is None
