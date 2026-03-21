"""Tests for the recipe model CRUD, search, rating, and favorites."""
import json
import pytest

from souschef.models.recipe import (
    add_recipe,
    get_recipe,
    edit_recipe,
    delete_recipe,
    list_recipes,
    search_recipes,
    rate_recipe,
    favorite_recipe,
)


SAMPLE_RECIPE = {
    "title": "Spaghetti Bolognese",
    "description": "A classic Italian meat sauce pasta.",
    "source_url": "https://example.com/bolognese",
    "source_type": "url",
    "prep_time_minutes": 15,
    "cook_time_minutes": 45,
    "servings": 4,
    "ingredients": ["200g spaghetti", "300g ground beef", "1 onion", "2 cloves garlic"],
    "instructions": ["Boil pasta", "Brown beef", "Simmer sauce", "Combine"],
    "notes": "Best served fresh.",
}


def test_add_recipe_from_json(db):
    recipe_id = add_recipe(db, SAMPLE_RECIPE)
    assert isinstance(recipe_id, int)
    assert recipe_id > 0


def test_view_recipe(db):
    recipe_id = add_recipe(db, SAMPLE_RECIPE)
    recipe = get_recipe(db, recipe_id)

    assert recipe is not None
    assert recipe["id"] == recipe_id
    assert recipe["title"] == "Spaghetti Bolognese"
    assert recipe["description"] == "A classic Italian meat sauce pasta."
    assert recipe["prep_time_minutes"] == 15
    assert recipe["cook_time_minutes"] == 45
    assert recipe["servings"] == 4

    # ingredients and instructions should be returned as Python objects (lists)
    ingredients = recipe["ingredients"]
    if isinstance(ingredients, str):
        ingredients = json.loads(ingredients)
    assert "200g spaghetti" in ingredients

    # getting a non-existent recipe should return None
    assert get_recipe(db, 99999) is None


def test_edit_recipe_merge_patch(db):
    recipe_id = add_recipe(db, SAMPLE_RECIPE)

    edit_recipe(db, recipe_id, {"title": "Tagliatelle Bolognese", "servings": 6})

    updated = get_recipe(db, recipe_id)
    assert updated["title"] == "Tagliatelle Bolognese"
    assert updated["servings"] == 6
    # unchanged fields must persist
    assert updated["description"] == "A classic Italian meat sauce pasta."
    assert updated["cook_time_minutes"] == 45


def test_delete_recipe(db):
    recipe_id = add_recipe(db, SAMPLE_RECIPE)
    assert get_recipe(db, recipe_id) is not None

    delete_recipe(db, recipe_id)
    assert get_recipe(db, recipe_id) is None


def test_list_recipes(db):
    id1 = add_recipe(db, SAMPLE_RECIPE)
    id2 = add_recipe(db, {**SAMPLE_RECIPE, "title": "Penne Arrabbiata"})

    recipes = list_recipes(db)
    ids = [r["id"] for r in recipes]
    assert id1 in ids
    assert id2 in ids


def test_rate_recipe(db):
    recipe_id = add_recipe(db, SAMPLE_RECIPE)
    rate_recipe(db, recipe_id, 4)

    recipe = get_recipe(db, recipe_id)
    assert recipe["rating"] == 4


def test_favorite_recipe(db):
    recipe_id = add_recipe(db, SAMPLE_RECIPE)

    favorite_recipe(db, recipe_id, True)
    recipe = get_recipe(db, recipe_id)
    assert recipe["is_favorite"] in (1, True)

    favorite_recipe(db, recipe_id, False)
    recipe = get_recipe(db, recipe_id)
    assert recipe["is_favorite"] in (0, False)


def test_list_recipes_with_filters(db):
    fav_id = add_recipe(db, {**SAMPLE_RECIPE, "title": "Favorite Pasta"})
    unfav_id = add_recipe(db, {**SAMPLE_RECIPE, "title": "Regular Pasta"})

    favorite_recipe(db, fav_id, True)

    favorites = list_recipes(db, favorite=True)
    fav_ids = [r["id"] for r in favorites]
    assert fav_id in fav_ids
    assert unfav_id not in fav_ids


def test_search_recipes(db):
    target_id = add_recipe(db, {**SAMPLE_RECIPE, "title": "Unique Mango Cake"})
    other_id = add_recipe(db, {**SAMPLE_RECIPE, "title": "Plain Rice Dish"})

    results = search_recipes(db, "Mango")
    result_ids = [r["id"] for r in results]
    assert target_id in result_ids
    assert other_id not in result_ids
