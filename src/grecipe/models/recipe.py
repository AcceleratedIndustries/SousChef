"""Recipe model: CRUD, search, rating, and favorites."""
import json
from datetime import datetime, timezone

EDITABLE_FIELDS = {
    "title",
    "description",
    "source_url",
    "source_type",
    "prep_time_minutes",
    "cook_time_minutes",
    "servings",
    "ingredients",
    "instructions",
    "image_path",
    "rating",
    "notes",
    "is_favorite",
}

_JSON_FIELDS = {"ingredients", "instructions"}


def _encode(value, field):
    """JSON-encode a value if it's a JSON field and not already a string."""
    if field in _JSON_FIELDS and not isinstance(value, str):
        return json.dumps(value)
    return value


def _row_to_dict(row):
    """Convert a sqlite3.Row to a plain dict."""
    if row is None:
        return None
    return dict(row)


def add_recipe(conn, data):
    """Insert a new recipe and return the new row ID."""
    allowed = {"title", "description", "source_url", "source_type",
                "prep_time_minutes", "cook_time_minutes", "servings",
                "ingredients", "instructions", "image_path", "rating",
                "notes", "is_favorite"}
    filtered = {k: _encode(v, k) for k, v in data.items() if k in allowed}

    if not filtered.get("title"):
        raise ValueError("title is required")

    columns = ", ".join(filtered.keys())
    placeholders = ", ".join("?" for _ in filtered)
    values = list(filtered.values())

    cur = conn.execute(
        f"INSERT INTO recipes ({columns}) VALUES ({placeholders})",
        values,
    )
    conn.commit()
    return cur.lastrowid


def get_recipe(conn, recipe_id):
    """Return a single recipe as a dict, or None if not found."""
    conn.row_factory = _dict_row_factory
    row = conn.execute(
        "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()
    conn.row_factory = None
    return row


def _dict_row_factory(cursor, row):
    """sqlite3 row factory that returns plain dicts."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def edit_recipe(conn, recipe_id, changes):
    """Merge-patch update: only update the provided fields."""
    updates = {
        k: _encode(v, k)
        for k, v in changes.items()
        if k in EDITABLE_FIELDS
    }
    if not updates:
        return

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    set_clause = ", ".join(f"{col} = ?" for col in updates)
    values = list(updates.values()) + [recipe_id]

    conn.execute(
        f"UPDATE recipes SET {set_clause} WHERE id = ?",
        values,
    )
    conn.commit()


def delete_recipe(conn, recipe_id):
    """Delete a recipe by ID."""
    conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    conn.commit()


def list_recipes(
    conn,
    tag=None,
    category=None,
    favorite=None,
    limit=None,
    offset=None,
    sort="date",
):
    """Return a list of recipes with optional filters.

    sort: 'date' (default, newest first), 'rating', 'title'
    """
    query = "SELECT DISTINCT r.* FROM recipes r"
    joins = []
    conditions = []
    params = []

    if tag is not None:
        joins.append(
            "JOIN recipe_tags rt ON rt.recipe_id = r.id "
            "JOIN tags t ON t.id = rt.tag_id"
        )
        conditions.append("t.name = ?")
        params.append(tag)

    if category is not None:
        joins.append(
            "JOIN recipe_meal_categories rmc ON rmc.recipe_id = r.id "
            "JOIN meal_categories mc ON mc.id = rmc.meal_category_id"
        )
        conditions.append("mc.name = ?")
        params.append(category)

    if favorite is not None:
        conditions.append("r.is_favorite = ?")
        params.append(1 if favorite else 0)

    if joins:
        query += " " + " ".join(joins)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    sort_map = {
        "date": "r.created_at DESC",
        "rating": "r.rating DESC",
        "title": "r.title ASC",
    }
    query += f" ORDER BY {sort_map.get(sort, 'r.created_at DESC')}"

    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)
    if offset is not None:
        query += " OFFSET ?"
        params.append(offset)

    conn.row_factory = _dict_row_factory
    rows = conn.execute(query, params).fetchall()
    conn.row_factory = None
    return rows


def search_recipes(conn, query):
    """LIKE search across title, description, and ingredients."""
    pattern = f"%{query}%"
    conn.row_factory = _dict_row_factory
    rows = conn.execute(
        """
        SELECT * FROM recipes
        WHERE title LIKE ?
           OR description LIKE ?
           OR ingredients LIKE ?
        ORDER BY created_at DESC
        """,
        (pattern, pattern, pattern),
    ).fetchall()
    conn.row_factory = None
    return rows


def rate_recipe(conn, recipe_id, rating):
    """Set rating (1-5) for a recipe."""
    if rating not in range(1, 6):
        raise ValueError("rating must be between 1 and 5")
    conn.execute(
        "UPDATE recipes SET rating = ?, updated_at = ? WHERE id = ?",
        (rating, datetime.now(timezone.utc).isoformat(), recipe_id),
    )
    conn.commit()


def favorite_recipe(conn, recipe_id, value):
    """Set or unset favorite status for a recipe."""
    conn.execute(
        "UPDATE recipes SET is_favorite = ?, updated_at = ? WHERE id = ?",
        (1 if value else 0, datetime.now(timezone.utc).isoformat(), recipe_id),
    )
    conn.commit()
