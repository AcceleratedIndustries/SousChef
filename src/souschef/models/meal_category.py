"""Meal category model: set and get meal categories for recipes."""


def set_categories(conn, recipe_id, category_names):
    """Set meal categories for a recipe, replacing any existing associations.

    Looks up category IDs from the meal_categories table by name.
    Unknown category names are silently skipped.
    """
    conn.execute(
        "DELETE FROM recipe_meal_categories WHERE recipe_id = ?",
        (recipe_id,),
    )
    for name in category_names:
        normalized = name.strip().lower()
        if not normalized:
            continue
        conn.execute(
            """
            INSERT OR IGNORE INTO recipe_meal_categories (recipe_id, meal_category_id)
            SELECT ?, id FROM meal_categories WHERE name = ?
            """,
            (recipe_id, normalized),
        )
    conn.commit()


def get_categories(conn, recipe_id):
    """Return a list of meal category name strings for a recipe."""
    rows = conn.execute(
        """
        SELECT mc.name
        FROM meal_categories mc
        JOIN recipe_meal_categories rmc ON rmc.meal_category_id = mc.id
        WHERE rmc.recipe_id = ?
        ORDER BY mc.name ASC
        """,
        (recipe_id,),
    ).fetchall()
    return [row[0] for row in rows]
