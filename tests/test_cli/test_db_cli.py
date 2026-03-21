"""Tests for db CLI commands."""
import json
import pytest
from typer.testing import CliRunner
from grecipe.cli.main import app

runner = CliRunner()


def test_db_init_and_stats(tmp_path, monkeypatch):
    monkeypatch.setenv("GRECIPE_DB_DIR", str(tmp_path))
    init_result = runner.invoke(app, ["db", "init"])
    assert init_result.exit_code == 0, init_result.output
    init_data = json.loads(init_result.output)
    assert init_data["status"] == "ok"
    stats_result = runner.invoke(app, ["db", "stats"])
    assert stats_result.exit_code == 0, stats_result.output
    stats_data = json.loads(stats_result.output)
    assert stats_data["recipes"] == 0
    assert stats_data["tags"] == 0
    assert stats_data["meal_plans"] == 0
    assert stats_data["grocery_lists"] == 0
    assert stats_data["chat_log"] == 0
