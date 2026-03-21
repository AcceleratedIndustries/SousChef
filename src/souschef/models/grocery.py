"""Grocery list model: CRUD, item management, and plan-based generation."""
import json

from souschef.db.connection import dict_rows
from souschef.units import (
    normalize_unit,
    can_combine,
    combine_quantities,
    infer_store_section,
)


# ---------------------------------------------------------------------------
# List CRUD
# ---------------------------------------------------------------------------

def create_list(conn, name, meal_plan_id=None):
    """Create a grocery_lists row and return its ID."""
    cur = conn.execute(
        "INSERT INTO grocery_lists (name, meal_plan_id) VALUES (?, ?)",
        (name, meal_plan_id),
    )
    conn.commit()
    return cur.lastrowid


def get_list(conn, list_id):
    """Return a grocery list dict or None."""
    with dict_rows(conn) as c:
        row = c.execute(
            "SELECT * FROM grocery_lists WHERE id = ?", (list_id,)
        ).fetchone()
    return row


def delete_list(conn, list_id):
    """Delete a grocery list (cascades to items). Returns True if deleted, False if not found."""
    cur = conn.execute("DELETE FROM grocery_lists WHERE id = ?", (list_id,))
    conn.commit()
    return cur.rowcount > 0


def list_lists(conn):
    """Return all grocery lists ordered by created_at DESC."""
    with dict_rows(conn) as c:
        rows = c.execute(
            "SELECT * FROM grocery_lists ORDER BY created_at DESC"
        ).fetchall()
    return rows


# ---------------------------------------------------------------------------
# Item management
# ---------------------------------------------------------------------------

def add_item(conn, list_id, name, quantity=None, unit=None, store_section=None):
    """Insert a grocery item. Infers store_section if not provided. Returns item ID."""
    if store_section is None:
        store_section = infer_store_section(name)

    cur = conn.execute(
        """
        INSERT INTO grocery_items (grocery_list_id, name, quantity, unit, store_section)
        VALUES (?, ?, ?, ?, ?)
        """,
        (list_id, name, quantity, unit, store_section),
    )
    conn.commit()
    return cur.lastrowid


def check_item(conn, list_id, item_id, checked=True):
    """Set is_checked for an item."""
    conn.execute(
        "UPDATE grocery_items SET is_checked = ? WHERE id = ? AND grocery_list_id = ?",
        (1 if checked else 0, item_id, list_id),
    )
    conn.commit()


def get_items(conn, list_id):
    """Return items for a list ordered by store_section, name."""
    with dict_rows(conn) as c:
        rows = c.execute(
            """
            SELECT * FROM grocery_items
            WHERE grocery_list_id = ?
            ORDER BY store_section, name
            """,
            (list_id,),
        ).fetchall()
    return rows


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_list(conn, list_id):
    """Return a plain-text markdown representation of the grocery list."""
    gl = get_list(conn, list_id)
    if gl is None:
        return None

    items = get_items(conn, list_id)
    if not items:
        return f"# {gl['name']}\n\n(empty)\n"

    # Group by section
    sections = {}
    for item in items:
        section = item["store_section"] or "other"
        sections.setdefault(section, []).append(item)

    lines = [f"# {gl['name']}", ""]
    for section, section_items in sorted(sections.items()):
        lines.append(f"## {section.title()}")
        for item in section_items:
            checkbox = "[x]" if item["is_checked"] else "[ ]"
            qty_str = ""
            if item["quantity"] is not None:
                qty_str = f" {item['quantity']}"
                if item["unit"]:
                    qty_str += f" {item['unit']}"
            lines.append(f"- {checkbox} {item['name']}{qty_str}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Generate from meal plan
# ---------------------------------------------------------------------------

def generate_from_plan(conn, plan_id, servings_multiplier=1.0):
    """Aggregate ingredients from all recipes in a plan and create a grocery list.

    Normalizes units, combines compatible quantities, infers store sections.
    When units can't be combined, creates separate line items with an alt_key
    like "{name} ({unit})".

    Returns the new grocery list ID.
    """
    with dict_rows(conn) as c:
        plan = c.execute(
            "SELECT * FROM meal_plans WHERE id = ?", (plan_id,)
        ).fetchone()
    if plan is None:
        raise ValueError(f"Meal plan {plan_id!r} not found")

    # Fetch all plan items with recipe info
    with dict_rows(conn) as c:
        plan_items = c.execute(
            """
            SELECT mpi.*, r.ingredients, r.servings
            FROM meal_plan_items mpi
            JOIN recipes r ON r.id = mpi.recipe_id
            WHERE mpi.meal_plan_id = ?
            """,
            (plan_id,),
        ).fetchall()

    # Aggregate: key -> {"quantity": float, "unit": str, "section": str}
    # If a name already exists with a different incompatible unit, use alt_key.
    aggregated = {}  # key -> {"quantity": float, "unit": str | None}

    for plan_item in plan_items:
        raw_ingredients = plan_item.get("ingredients")
        if not raw_ingredients:
            continue
        if isinstance(raw_ingredients, str):
            try:
                ingredients = json.loads(raw_ingredients)
            except (json.JSONDecodeError, TypeError):
                continue
        else:
            ingredients = raw_ingredients

        recipe_servings = plan_item.get("servings") or 1
        servings_override = plan_item.get("servings_override")
        multiplier = servings_multiplier
        if servings_override is not None:
            multiplier *= servings_override / recipe_servings

        for ing in ingredients:
            if not isinstance(ing, dict):
                continue
            name = (ing.get("name") or "").strip()
            if not name:
                continue

            raw_qty = ing.get("quantity")
            raw_unit = ing.get("unit")

            quantity = float(raw_qty) * multiplier if raw_qty is not None else None
            unit = normalize_unit(raw_unit) if raw_unit else None

            # Determine key
            key = name
            if key in aggregated:
                existing = aggregated[key]
                existing_unit = existing["unit"]
                if quantity is not None and existing["quantity"] is not None:
                    if existing_unit == unit or (
                        existing_unit is not None
                        and unit is not None
                        and can_combine(existing_unit, unit)
                    ):
                        # Combine
                        if existing_unit is None or unit is None:
                            aggregated[key]["quantity"] += quantity
                        else:
                            new_qty, new_unit = combine_quantities(
                                existing["quantity"], existing_unit,
                                quantity, unit,
                            )
                            aggregated[key]["quantity"] = new_qty
                            aggregated[key]["unit"] = new_unit
                    else:
                        # Incompatible units -- use alt_key
                        alt_key = f"{name} ({unit})" if unit else f"{name} (each)"
                        if alt_key in aggregated:
                            aggregated[alt_key]["quantity"] += quantity
                        else:
                            aggregated[alt_key] = {"quantity": quantity, "unit": unit}
                else:
                    # One or both quantities are None -- skip combining
                    pass
            else:
                aggregated[key] = {"quantity": quantity, "unit": unit}

    # Create grocery list
    list_name = f"Groceries for {plan['name']}"
    list_id = create_list(conn, list_name, meal_plan_id=plan_id)

    for item_name, data in aggregated.items():
        section = infer_store_section(item_name.split(" (")[0])
        add_item(
            conn,
            list_id,
            item_name,
            quantity=data["quantity"],
            unit=data["unit"],
            store_section=section,
        )

    return list_id
