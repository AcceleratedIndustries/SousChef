"""Recipe history model: track changes to recipes over time."""
import json


def _dict_row_factory(cursor, row):
    """sqlite3 row factory that returns plain dicts."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def record_change(conn, recipe_id, changes, old_recipe, chat_log_id=None):
    """Record a recipe modification.

    Stores changed_fields (list of keys from changes dict) and
    previous_values (old values for those fields from old_recipe) as JSON.
    Returns the history entry ID.
    """
    changed_fields = list(changes.keys())
    previous_values = {k: old_recipe.get(k) for k in changed_fields}

    cur = conn.execute(
        """
        INSERT INTO recipe_history (recipe_id, changed_fields, previous_values, chat_log_id)
        VALUES (?, ?, ?, ?)
        """,
        (
            recipe_id,
            json.dumps(changed_fields),
            json.dumps(previous_values),
            chat_log_id,
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_history(conn, recipe_id):
    """Get modification history for a recipe, ordered by changed_at DESC.

    JSON-decodes changed_fields and previous_values in the returned dicts.
    """
    conn.row_factory = _dict_row_factory
    rows = conn.execute(
        """
        SELECT * FROM recipe_history
        WHERE recipe_id = ?
        ORDER BY changed_at DESC
        """,
        (recipe_id,),
    ).fetchall()
    conn.row_factory = None

    for row in rows:
        if isinstance(row["changed_fields"], str):
            row["changed_fields"] = json.loads(row["changed_fields"])
        if isinstance(row["previous_values"], str):
            row["previous_values"] = json.loads(row["previous_values"])

    return rows
