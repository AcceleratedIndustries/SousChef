"""Dietary model: set and get dietary flags for recipes."""


def set_dietary(conn, recipe_id, flags):
    """Set dietary flags for a recipe, replacing any existing flags.

    Flag strings are normalized to lowercase and stripped of whitespace.
    """
    conn.execute(
        "DELETE FROM dietary_info WHERE recipe_id = ?",
        (recipe_id,),
    )
    for flag in flags:
        normalized = flag.strip().lower()
        if not normalized:
            continue
        conn.execute(
            "INSERT OR IGNORE INTO dietary_info (recipe_id, flag) VALUES (?, ?)",
            (recipe_id, normalized),
        )
    conn.commit()


def get_dietary(conn, recipe_id):
    """Return a list of dietary flag strings for a recipe, ordered alphabetically."""
    rows = conn.execute(
        """
        SELECT flag FROM dietary_info
        WHERE recipe_id = ?
        ORDER BY flag ASC
        """,
        (recipe_id,),
    ).fetchall()
    return [row[0] for row in rows]
