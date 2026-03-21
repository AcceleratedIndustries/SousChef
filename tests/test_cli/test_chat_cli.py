"""Tests for chat CLI commands."""
import json
import pytest
from typer.testing import CliRunner
from grecipe.cli.main import app

runner = CliRunner()


def test_chat_log_and_search(tmp_path, monkeypatch):
    monkeypatch.setenv("GRECIPE_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    log_result = runner.invoke(
        app,
        [
            "chat", "log",
            "--action", "add_recipe",
            "--user-message", "add my taco recipe",
        ],
    )
    assert log_result.exit_code == 0, log_result.output
    log_data = json.loads(log_result.output)
    assert log_data["id"] == 1
    assert log_data["status"] == "logged"

    search_result = runner.invoke(app, ["chat", "search", "taco"])
    assert search_result.exit_code == 0, search_result.output
    search_data = json.loads(search_result.output)
    assert len(search_data) == 1
    assert "taco" in search_data[0]["user_message"]
