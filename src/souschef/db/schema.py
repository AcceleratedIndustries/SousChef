"""Database schema creation and migration."""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    source_url TEXT,
    source_type TEXT CHECK(source_type IN ('url', 'text', 'other')),
    prep_time_minutes INTEGER,
    cook_time_minutes INTEGER,
    servings INTEGER,
    ingredients JSON,
    instructions JSON,
    image_path TEXT,
    rating INTEGER CHECK(rating BETWEEN 1 AND 5),
    notes TEXT,
    is_favorite BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS recipe_tags (
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (recipe_id, tag_id)
);

CREATE TABLE IF NOT EXISTS meal_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS recipe_meal_categories (
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    meal_category_id INTEGER NOT NULL REFERENCES meal_categories(id) ON DELETE CASCADE,
    PRIMARY KEY (recipe_id, meal_category_id)
);

CREATE TABLE IF NOT EXISTS dietary_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    flag TEXT NOT NULL,
    UNIQUE(recipe_id, flag)
);

CREATE TABLE IF NOT EXISTS meal_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS meal_plan_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meal_plan_id INTEGER NOT NULL REFERENCES meal_plans(id) ON DELETE CASCADE,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    meal_category_id INTEGER NOT NULL REFERENCES meal_categories(id),
    servings_override INTEGER
);

CREATE TABLE IF NOT EXISTS grocery_lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meal_plan_id INTEGER REFERENCES meal_plans(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS grocery_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grocery_list_id INTEGER NOT NULL REFERENCES grocery_lists(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    quantity REAL,
    unit TEXT,
    store_section TEXT,
    is_checked BOOLEAN DEFAULT 0,
    source_recipes JSON
);

CREATE TABLE IF NOT EXISTS chat_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_message TEXT,
    assistant_response TEXT,
    action_type TEXT,
    entity_type TEXT,
    entity_id INTEGER
);

CREATE VIRTUAL TABLE IF NOT EXISTS chat_log_fts USING fts5(
    user_message,
    assistant_response,
    content='chat_log',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS chat_log_ai AFTER INSERT ON chat_log BEGIN
    INSERT INTO chat_log_fts(rowid, user_message, assistant_response)
    VALUES (new.id, new.user_message, new.assistant_response);
END;

CREATE TRIGGER IF NOT EXISTS chat_log_ad AFTER DELETE ON chat_log BEGIN
    INSERT INTO chat_log_fts(chat_log_fts, rowid, user_message, assistant_response)
    VALUES ('delete', old.id, old.user_message, old.assistant_response);
END;

CREATE TRIGGER IF NOT EXISTS chat_log_au AFTER UPDATE ON chat_log BEGIN
    INSERT INTO chat_log_fts(chat_log_fts, rowid, user_message, assistant_response)
    VALUES ('delete', old.id, old.user_message, old.assistant_response);
    INSERT INTO chat_log_fts(rowid, user_message, assistant_response)
    VALUES (new.id, new.user_message, new.assistant_response);
END;

CREATE TABLE IF NOT EXISTS recipe_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    changed_fields JSON,
    previous_values JSON,
    chat_log_id INTEGER REFERENCES chat_log(id),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db(conn):
    """Create all tables."""
    conn.executescript(SCHEMA_SQL)
