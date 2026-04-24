"""SousChef MCP server entry point."""

from mcp.server.fastmcp import FastMCP

from souschef.db.connection import get_db, get_db_path
from souschef.db.schema import init_db
from souschef.db.seed import seed_meal_categories
from souschef.mcp import tools as _tools


def _ensure_db_initialized() -> None:
    """Run schema init + seed on first launch so the user never has to."""
    conn = get_db(get_db_path())
    try:
        init_db(conn)
        seed_meal_categories(conn)
        conn.commit()
    finally:
        conn.close()


mcp = FastMCP("souschef")
_tools.register(mcp)


def main() -> None:
    _ensure_db_initialized()
    mcp.run()


if __name__ == "__main__":
    main()
