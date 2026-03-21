"""Tests for plan CLI commands."""
import json
import pytest
from typer.testing import CliRunner
from grecipe.cli.main import app

runner = CliRunner()


def test_plan_create_and_view(tmp_path, monkeypatch):
    monkeypatch.setenv("GRECIPE_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    result = runner.invoke(app, ["plan", "create", "--name", "Week 1"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["id"] == 1
    assert data["status"] == "created"

    view_result = runner.invoke(app, ["plan", "view", "1"])
    assert view_result.exit_code == 0, view_result.output
    view_data = json.loads(view_result.output)
    assert view_data["name"] == "Week 1"
    assert "items" in view_data


def test_plan_add_item(tmp_path, monkeypatch):
    monkeypatch.setenv("GRECIPE_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    # Add a recipe first
    recipe_data = json.dumps({"title": "Tacos"})
    runner.invoke(app, ["recipe", "add", "--json", recipe_data])
    # Create a plan
    runner.invoke(app, ["plan", "create", "--name", "Dinner Plan"])
    # Add item to plan
    result = runner.invoke(
        app,
        ["plan", "add", "1", "1", "--date", "2026-03-21", "--meal", "dinner"],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["item_id"] == 1
    assert data["status"] == "added"


def test_plan_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("GRECIPE_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    runner.invoke(app, ["plan", "create", "--name", "To Delete"])
    result = runner.invoke(app, ["plan", "delete", "1"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["id"] == 1
    assert data["status"] == "deleted"
