"""Tests for recipe CLI commands."""
import json
import pytest
from typer.testing import CliRunner
from souschef.cli.main import app

runner = CliRunner()


def test_db_init_then_recipe_add(tmp_path, monkeypatch):
    monkeypatch.setenv("SOUSCHEF_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    recipe_data = json.dumps({"title": "Pasta Carbonara", "description": "Classic Italian"})
    result = runner.invoke(app, ["recipe", "add", "--json", recipe_data])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["id"] == 1
    assert data["status"] == "created"


def test_recipe_view(tmp_path, monkeypatch):
    monkeypatch.setenv("SOUSCHEF_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    recipe_data = json.dumps({"title": "Tacos"})
    runner.invoke(app, ["recipe", "add", "--json", recipe_data])
    result = runner.invoke(app, ["recipe", "view", "1"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["title"] == "Tacos"


def test_recipe_list(tmp_path, monkeypatch):
    monkeypatch.setenv("SOUSCHEF_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    runner.invoke(app, ["recipe", "add", "--json", json.dumps({"title": "Recipe A"})])
    runner.invoke(app, ["recipe", "add", "--json", json.dumps({"title": "Recipe B"})])
    result = runner.invoke(app, ["recipe", "list"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert len(data) == 2


def test_recipe_edit(tmp_path, monkeypatch):
    monkeypatch.setenv("SOUSCHEF_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    runner.invoke(app, ["recipe", "add", "--json", json.dumps({"title": "Original Title"})])
    edit_data = json.dumps({"title": "Updated Title"})
    edit_result = runner.invoke(app, ["recipe", "edit", "1", "--json", edit_data])
    assert edit_result.exit_code == 0, edit_result.output
    result = runner.invoke(app, ["recipe", "view", "1"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["title"] == "Updated Title"


def test_recipe_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("SOUSCHEF_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    runner.invoke(app, ["recipe", "add", "--json", json.dumps({"title": "To Be Deleted"})])
    delete_result = runner.invoke(app, ["recipe", "delete", "1"])
    assert delete_result.exit_code == 0, delete_result.output
    del_data = json.loads(delete_result.output)
    assert del_data["status"] == "deleted"
    list_result = runner.invoke(app, ["recipe", "list"])
    data = json.loads(list_result.output)
    assert len(data) == 0
