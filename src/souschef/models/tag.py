"""Tag model: add, remove, and list tags for recipes."""


def add_tags(conn, recipe_id, tag_names):
    """Add tags to a recipe, creating tags if they don't exist.

    Tag names are normalized to lowercase and stripped of whitespace.
    """
    for name in tag_names:
        normalized = name.strip().lower()
        if not normalized:
            continue
        conn.execute(
            "INSERT OR IGNORE INTO tags (name) VALUES (?)",
            (normalized,),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO recipe_tags (recipe_id, tag_id)
            SELECT ?, id FROM tags WHERE name = ?
            """,
            (recipe_id, normalized),
        )
    conn.commit()


def remove_tag(conn, recipe_id, tag_name):
    """Remove a tag from a recipe."""
    normalized = tag_name.strip().lower()
    conn.execute(
        """
        DELETE FROM recipe_tags
        WHERE recipe_id = ?
          AND tag_id = (SELECT id FROM tags WHERE name = ?)
        """,
        (recipe_id, normalized),
    )
    conn.commit()


def get_tags_for_recipe(conn, recipe_id):
    """Return a list of tag name strings for a recipe, ordered by name."""
    rows = conn.execute(
        """
        SELECT t.name
        FROM tags t
        JOIN recipe_tags rt ON rt.tag_id = t.id
        WHERE rt.recipe_id = ?
        ORDER BY t.name
        """,
        (recipe_id,),
    ).fetchall()
    return [row[0] for row in rows]


def list_tags(conn):
    """Return a list of {"name": str, "count": int} dicts, ordered by count DESC."""
    rows = conn.execute(
        """
        SELECT t.name, COUNT(rt.recipe_id) AS count
        FROM tags t
        JOIN recipe_tags rt ON rt.tag_id = t.id
        GROUP BY t.id, t.name
        ORDER BY count DESC, t.name ASC
        """,
    ).fetchall()
    return [{"name": row[0], "count": row[1]} for row in rows]
