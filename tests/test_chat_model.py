"""Tests for the chat log model."""
import pytest
from souschef.models.chat import log_chat, search_chat


def test_log_chat(db):
    """Log a chat entry and verify it can be found via FTS search."""
    log_chat(
        db,
        user_message="add my taco recipe",
        assistant_response="I've added your taco recipe.",
        action_type="add_recipe",
    )

    results = search_chat(db, "taco")
    assert len(results) == 1
    assert results[0]["action_type"] == "add_recipe"


def test_search_chat_no_results(db):
    """Search for a term that doesn't exist returns an empty list."""
    results = search_chat(db, "nonexistent")
    assert results == []
