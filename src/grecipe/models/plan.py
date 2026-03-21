"""Meal plan model: CRUD, items, and recipe suggestions."""
from datetime import datetime, timezone

from grecipe.db.connection import dict_rows


def _now():
    return datetime.now(timezone.utc).isoformat()


def create_plan(conn, name, start_date=None, end_date=None):
    """Insert a meal_plans row and return the plan ID."""
    cur = conn.execute(
        "INSERT INTO meal_plans (name, start_date, end_date) VALUES (?, ?, ?)",
        (name, start_date, end_date),
    )
    conn.commit()
    return cur.lastrowid


def get_plan(conn, plan_id):
    """Return a plan dict or None if not found."""
    with dict_rows(conn) as c:
        row = c.execute(
            "SELECT * FROM meal_plans WHERE id = ?", (plan_id,)
        ).fetchone()
    return row


def edit_plan(conn, plan_id, name=None, start_date=None, end_date=None):
    """Update only non-None fields, always update updated_at."""
    updates = {}
    if name is not None:
        updates["name"] = name
    if start_date is not None:
        updates["start_date"] = start_date
    if end_date is not None:
        updates["end_date"] = end_date
    updates["updated_at"] = _now()

    set_clause = ", ".join(f"{col} = ?" for col in updates)
    values = list(updates.values()) + [plan_id]
    conn.execute(f"UPDATE meal_plans SET {set_clause} WHERE id = ?", values)
    conn.commit()


def delete_plan(conn, plan_id):
    """Delete a plan (cascade deletes items). Returns True if deleted, False if not found."""
    cur = conn.execute("DELETE FROM meal_plans WHERE id = ?", (plan_id,))
    conn.commit()
    return cur.rowcount > 0


def add_plan_item(conn, plan_id, recipe_id, date, meal_category, servings_override=None):
    """Insert a meal_plan_items row. Looks up meal_category by name (lowercase).

    Raises ValueError if the category is not found. Updates meal_plans.updated_at.
    Returns the new item ID.
    """
    row = conn.execute(
        "SELECT id FROM meal_categories WHERE name = ?",
        (meal_category.lower(),),
    ).fetchone()
    if row is None:
        raise ValueError(f"Unknown meal category: {meal_category!r}")

    meal_category_id = row[0]

    cur = conn.execute(
        """
        INSERT INTO meal_plan_items
            (meal_plan_id, recipe_id, date, meal_category_id, servings_override)
        VALUES (?, ?, ?, ?, ?)
        """,
        (plan_id, recipe_id, date, meal_category_id, servings_override),
    )
    conn.execute(
        "UPDATE meal_plans SET updated_at = ? WHERE id = ?",
        (_now(), plan_id),
    )
    conn.commit()
    return cur.lastrowid


def remove_plan_item(conn, plan_id, item_id):
    """Delete from meal_plan_items where id and meal_plan_id both match.
    Returns True if deleted, False if not found."""
    cur = conn.execute(
        "DELETE FROM meal_plan_items WHERE id = ? AND meal_plan_id = ?",
        (item_id, plan_id),
    )
    conn.commit()
    return cur.rowcount > 0


def get_plan_items(conn, plan_id):
    """Return items for a plan joined with recipe and category info.

    Ordered by date, then meal_categories.id.
    """
    with dict_rows(conn) as c:
        rows = c.execute(
            """
            SELECT
                mpi.id,
                mpi.meal_plan_id,
                mpi.recipe_id,
                mpi.date,
                mpi.servings_override,
                r.title  AS recipe_title,
                r.image_path AS recipe_image_path,
                mc.name  AS meal_category
            FROM meal_plan_items mpi
            JOIN recipes r        ON r.id  = mpi.recipe_id
            JOIN meal_categories mc ON mc.id = mpi.meal_category_id
            WHERE mpi.meal_plan_id = ?
            ORDER BY mpi.date, mc.id
            """,
            (plan_id,),
        ).fetchall()
    return rows


def list_plans(conn):
    """Return all plans ordered by created_at DESC."""
    with dict_rows(conn) as c:
        rows = c.execute(
            "SELECT * FROM meal_plans ORDER BY created_at DESC"
        ).fetchall()
    return rows


def suggest_recipes(conn, limit=10):
    """Return recipes ordered by least-recently planned then highest rating.

    Uses LEFT JOIN so unplanned recipes (NULL last_planned) appear first.
    """
    with dict_rows(conn) as c:
        rows = c.execute(
            """
            SELECT
                r.*,
                MAX(mpi.date) AS last_planned
            FROM recipes r
            LEFT JOIN meal_plan_items mpi ON mpi.recipe_id = r.id
            GROUP BY r.id
            ORDER BY last_planned ASC NULLS FIRST, r.rating DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return rows
