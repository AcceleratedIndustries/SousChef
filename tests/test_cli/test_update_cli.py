"""CLI tests for update commands."""

import json
from unittest.mock import patch

from typer.testing import CliRunner
from souschef.cli.main import app

runner = CliRunner()


def test_update_check_up_to_date():
    mock_result = {"status": "up_to_date", "version": "abc1234"}
    with patch("souschef.cli.update.get_repo_root", return_value="/fake/path"), \
         patch("souschef.cli.update.check_for_updates", return_value=mock_result):
        result = runner.invoke(app, ["update", "check"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["status"] == "up_to_date"


def test_update_check_update_available():
    mock_result = {
        "status": "update_available", "current": "abc1234", "latest": "def5678",
        "commits_behind": 2, "changes": ["fix: bug", "feat: feature"],
    }
    with patch("souschef.cli.update.get_repo_root", return_value="/fake/path"), \
         patch("souschef.cli.update.check_for_updates", return_value=mock_result):
        result = runner.invoke(app, ["update", "check"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["status"] == "update_available"
    assert data["commits_behind"] == 2


def test_update_check_no_repo():
    with patch("souschef.cli.update.get_repo_root", return_value=None):
        result = runner.invoke(app, ["update", "check"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["status"] == "error"


def test_update_check_network_error():
    mock_result = {"status": "error", "error": "Could not reach remote"}
    with patch("souschef.cli.update.get_repo_root", return_value="/fake/path"), \
         patch("souschef.cli.update.check_for_updates", return_value=mock_result):
        result = runner.invoke(app, ["update", "check"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["status"] == "error"


def test_update_apply_success():
    mock_result = {"status": "updated", "previous": "abc1234", "current": "def5678", "changes": ["fix: something"]}
    with patch("souschef.cli.update.get_repo_root", return_value="/fake/path"), \
         patch("souschef.cli.update.apply_update", return_value=mock_result):
        result = runner.invoke(app, ["update", "apply"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["status"] == "updated"


def test_update_apply_dirty_tree():
    mock_result = {"status": "error", "error": "Working tree has uncommitted changes"}
    with patch("souschef.cli.update.get_repo_root", return_value="/fake/path"), \
         patch("souschef.cli.update.apply_update", return_value=mock_result):
        result = runner.invoke(app, ["update", "apply"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert "uncommitted" in data["error"]


def test_update_apply_up_to_date():
    mock_result = {"status": "up_to_date", "version": "abc1234"}
    with patch("souschef.cli.update.get_repo_root", return_value="/fake/path"), \
         patch("souschef.cli.update.apply_update", return_value=mock_result):
        result = runner.invoke(app, ["update", "apply"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["status"] == "up_to_date"


def test_update_apply_no_repo():
    with patch("souschef.cli.update.get_repo_root", return_value=None):
        result = runner.invoke(app, ["update", "apply"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["status"] == "error"


def test_update_check_exits_0_on_update_available():
    """update_available is not an error — should exit 0."""
    mock_result = {"status": "update_available", "current": "a", "latest": "b", "commits_behind": 1, "changes": ["x"]}
    with patch("souschef.cli.update.get_repo_root", return_value="/fake/path"), \
         patch("souschef.cli.update.check_for_updates", return_value=mock_result):
        result = runner.invoke(app, ["update", "check"])
    assert result.exit_code == 0
