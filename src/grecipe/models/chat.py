"""Chat log model: log and search chat interactions using FTS5."""


def _dict_row_factory(cursor, row):
    """sqlite3 row factory that returns plain dicts."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def log_chat(
    conn,
    user_message=None,
    assistant_response=None,
    action_type=None,
    entity_type=None,
    entity_id=None,
):
    """Insert a chat log entry into the chat_log table.

    The FTS5 trigger auto-populates chat_log_fts.
    Returns the log entry ID.
    """
    cur = conn.execute(
        """
        INSERT INTO chat_log (user_message, assistant_response, action_type, entity_type, entity_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_message, assistant_response, action_type, entity_type, entity_id),
    )
    conn.commit()
    return cur.lastrowid


def search_chat(conn, query):
    """Full-text search using FTS5 MATCH on chat_log_fts.

    Joins back to chat_log for full row data.
    Returns list of dicts ordered by timestamp DESC.
    """
    conn.row_factory = _dict_row_factory
    rows = conn.execute(
        """
        SELECT cl.*
        FROM chat_log cl
        JOIN chat_log_fts fts ON fts.rowid = cl.id
        WHERE chat_log_fts MATCH ?
        ORDER BY cl.timestamp DESC
        """,
        (query,),
    ).fetchall()
    conn.row_factory = None
    return rows
