"""Tests for grocery CLI commands."""
import json
import pytest
from typer.testing import CliRunner
from souschef.cli.main import app

runner = CliRunner()


def test_grocery_create_standalone(tmp_path, monkeypatch):
    monkeypatch.setenv("SOUSCHEF_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    result = runner.invoke(app, ["grocery", "create", "--name", "Weekly Shop"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["id"] == 1
    assert data["status"] == "created"


def test_grocery_add_item_and_view(tmp_path, monkeypatch):
    monkeypatch.setenv("SOUSCHEF_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    runner.invoke(app, ["grocery", "create", "--name", "My List"])
    add_result = runner.invoke(
        app,
        [
            "grocery", "add-item", "1",
            "--name", "milk",
            "--quantity", "1",
            "--unit", "gallon",
        ],
    )
    assert add_result.exit_code == 0, add_result.output
    add_data = json.loads(add_result.output)
    assert add_data["item_id"] == 1
    assert add_data["status"] == "added"

    view_result = runner.invoke(app, ["grocery", "view", "1"])
    assert view_result.exit_code == 0, view_result.output
    view_data = json.loads(view_result.output)
    assert len(view_data["items"]) == 1
    assert view_data["items"][0]["name"] == "milk"


def test_grocery_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("SOUSCHEF_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    runner.invoke(app, ["grocery", "create", "--name", "To Delete"])
    result = runner.invoke(app, ["grocery", "delete", "1"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["id"] == 1
    assert data["status"] == "deleted"


def test_grocery_list(tmp_path, monkeypatch):
    monkeypatch.setenv("SOUSCHEF_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    runner.invoke(app, ["grocery", "create", "--name", "List A"])
    runner.invoke(app, ["grocery", "create", "--name", "List B"])
    result = runner.invoke(app, ["grocery", "list"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert len(data) == 2
