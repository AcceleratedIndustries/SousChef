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
