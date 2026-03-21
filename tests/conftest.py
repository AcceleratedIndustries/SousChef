import pytest

@pytest.fixture
def db(tmp_path):
    """Provide a fresh in-memory-like DB in a temp directory."""
    from grecipe.db.connection import get_db
    from grecipe.db.schema import init_db
    from grecipe.db.seed import seed_meal_categories

    db_path = tmp_path / "test.db"
    conn = get_db(db_path)
    init_db(conn)
    seed_meal_categories(conn)
    yield conn
    conn.close()
