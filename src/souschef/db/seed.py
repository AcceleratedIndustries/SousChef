"""Seed data for the database."""

MEAL_CATEGORIES = [
    "breakfast", "lunch", "dinner", "snack",
    "brunch", "dessert", "side", "appetizer",
]


def seed_meal_categories(conn):
    """Insert default meal categories if they don't exist."""
    for name in MEAL_CATEGORIES:
        conn.execute(
            "INSERT OR IGNORE INTO meal_categories (name) VALUES (?)",
            (name,),
        )
    conn.commit()
