"""Tests for display CLI commands."""
import json
import pytest
from typer.testing import CliRunner
from grecipe.cli.main import app

runner = CliRunner()


def test_display_render_recipe(tmp_path, monkeypatch):
    monkeypatch.setenv("GRECIPE_DB_DIR", str(tmp_path))
    runner.invoke(app, ["db", "init"])
    recipe_data = json.dumps({"title": "Tacos"})
    runner.invoke(app, ["recipe", "add", "--json", recipe_data])
    result = runner.invoke(app, ["display", "render", "--recipe-id", "1"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "path" in data
    assert data["status"] == "rendered"
