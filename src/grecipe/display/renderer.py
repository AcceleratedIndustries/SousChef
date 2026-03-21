"""HTML rendering functions for recipes, meal plans, and grocery lists."""
import json
from collections import OrderedDict
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from grecipe.models.recipe import get_recipe
from grecipe.models.tag import get_tags_for_recipe
from grecipe.models.plan import get_plan, get_plan_items
from grecipe.models.grocery import get_list, get_items

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _get_env():
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=True,
    )


def _parse_json_field(value):
    """Parse a JSON string field, returning the parsed value or empty list."""
    if value is None:
        return []
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


def render_recipe(conn, recipe_id, output_dir):
    """Render a recipe to HTML and write to output_dir/recipe_{id}.html.

    Returns the Path to the written file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    recipe = get_recipe(conn, recipe_id)
    if recipe is None:
        raise ValueError(f"Recipe {recipe_id!r} not found")

    tags = get_tags_for_recipe(conn, recipe_id)
    ingredients = _parse_json_field(recipe.get("ingredients"))
    instructions = _parse_json_field(recipe.get("instructions"))

    env = _get_env()
    template = env.get_template("recipe.html")
    html = template.render(
        recipe=recipe,
        tags=tags,
        ingredients=ingredients,
        instructions=instructions,
    )

    output_path = output_dir / f"recipe_{recipe_id}.html"
    output_path.write_text(html, encoding="utf-8")
    return output_path


def render_plan(conn, plan_id, output_dir):
    """Render a meal plan to HTML and write to output_dir/plan_{id}.html.

    Items are grouped by date in an OrderedDict.
    Returns the Path to the written file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plan = get_plan(conn, plan_id)
    if plan is None:
        raise ValueError(f"Plan {plan_id!r} not found")

    items = get_plan_items(conn, plan_id)

    # Group items by date (OrderedDict preserves insertion order)
    items_by_date = OrderedDict()
    for item in items:
        date = item["date"]
        if date not in items_by_date:
            items_by_date[date] = []
        items_by_date[date].append(item)

    env = _get_env()
    template = env.get_template("plan.html")
    html = template.render(
        plan=plan,
        items_by_date=items_by_date,
    )

    output_path = output_dir / f"plan_{plan_id}.html"
    output_path.write_text(html, encoding="utf-8")
    return output_path


def render_grocery(conn, list_id, output_dir):
    """Render a grocery list to HTML and write to output_dir/grocery_{id}.html.

    Items are grouped by store_section in an OrderedDict.
    Returns the Path to the written file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    grocery_list = get_list(conn, list_id)
    if grocery_list is None:
        raise ValueError(f"Grocery list {list_id!r} not found")

    items = get_items(conn, list_id)

    # Group items by store_section (OrderedDict preserves insertion order)
    items_by_section = OrderedDict()
    for item in items:
        section = item.get("store_section") or "other"
        if section not in items_by_section:
            items_by_section[section] = []
        items_by_section[section].append(item)

    env = _get_env()
    template = env.get_template("grocery.html")
    html = template.render(
        grocery_list=grocery_list,
        items_by_section=items_by_section,
    )

    output_path = output_dir / f"grocery_{list_id}.html"
    output_path.write_text(html, encoding="utf-8")
    return output_path
