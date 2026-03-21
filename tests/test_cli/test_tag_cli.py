"""Tests for tag CLI commands."""
import json
import pytest
from typer.testing import CliRunner
from souschef.cli.main import app

runner = CliRunner()


def test_tag_add_and_list(tmp_path, monkeypatch):
    monkeypatch.setenv("SOUSCHEF_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    runner.invoke(app, ["recipe", "add", "--json", json.dumps({"title": "Tagged Recipe"})])
    add_result = runner.invoke(app, ["tag", "add", "1", "vegan", "gluten-free"])
    assert add_result.exit_code == 0, add_result.output
    add_data = json.loads(add_result.output)
    assert add_data["recipe_id"] == 1
    assert set(add_data["added"]) == {"vegan", "gluten-free"}
    list_result = runner.invoke(app, ["tag", "list"])
    assert list_result.exit_code == 0, list_result.output
    list_data = json.loads(list_result.output)
    assert len(list_data) == 2
