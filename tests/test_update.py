"""Tests for update logic."""

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from souschef.update import (
    get_repo_root,
    get_current_version,
    check_for_updates,
    is_working_tree_dirty,
)


def test_get_repo_root_finds_git_dir():
    root = get_repo_root()
    assert root is not None
    assert (root / ".git").exists()


def test_get_repo_root_returns_none_outside_git(tmp_path):
    fake_path = tmp_path / "src" / "souschef" / "update.py"
    fake_path.parent.mkdir(parents=True)
    fake_path.touch()
    with patch("souschef.update._THIS_FILE", fake_path):
        root = get_repo_root()
    assert root is None


def test_get_current_version():
    root = get_repo_root()
    version = get_current_version(root)
    assert version is not None
    assert len(version) == 7
    assert all(c in "0123456789abcdef" for c in version)


def test_is_working_tree_dirty_on_clean_repo():
    root = get_repo_root()
    dirty = is_working_tree_dirty(root)
    assert isinstance(dirty, bool)


def test_check_for_updates_with_mock():
    root = get_repo_root()

    def mock_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        cmd_str = " ".join(cmd)
        if "fetch" in cmd_str:
            pass
        elif "rev-parse HEAD" in cmd_str:
            result.stdout = "abc1234567890"
        elif "rev-parse origin/main" in cmd_str:
            result.stdout = "def5678901234"
        elif "rev-list" in cmd_str and "--count" in cmd_str:
            result.stdout = "3"
        elif "log" in cmd_str and "--format=%s" in cmd_str:
            result.stdout = "fix: something\nfeat: another\nchore: cleanup"
        return result

    with patch("souschef.update.subprocess.run", side_effect=mock_run):
        result = check_for_updates(root)

    assert result["status"] == "update_available"
    assert result["current"] == "abc1234"
    assert result["latest"] == "def5678"
    assert result["commits_behind"] == 3
    assert len(result["changes"]) == 3


def test_check_for_updates_when_up_to_date():
    root = get_repo_root()

    def mock_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = "abc1234567890"
        result.stderr = ""
        return result

    with patch("souschef.update.subprocess.run", side_effect=mock_run):
        result = check_for_updates(root)

    assert result["status"] == "up_to_date"
    assert result["version"] == "abc1234"


def test_check_for_updates_network_error():
    root = get_repo_root()

    def mock_run(cmd, **kwargs):
        result = MagicMock()
        if "fetch" in " ".join(cmd):
            result.returncode = 128
            result.stdout = ""
            result.stderr = "fatal: Could not read from remote repository."
        else:
            result.returncode = 0
            result.stdout = "abc1234567890"
            result.stderr = ""
        return result

    with patch("souschef.update.subprocess.run", side_effect=mock_run):
        result = check_for_updates(root)

    assert result["status"] == "error"
    assert "remote" in result["error"].lower() or "Could not" in result["error"]


def test_apply_update_success():
    from souschef.update import apply_update
    root = get_repo_root()
    call_count = {"n": 0}

    def mock_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        cmd_str = " ".join(str(c) for c in cmd)
        if "status --porcelain" in cmd_str:
            result.stdout = ""
        elif "rev-parse HEAD" in cmd_str:
            call_count["n"] += 1
            result.stdout = "abc1234567890" if call_count["n"] == 1 else "def5678901234"
        elif "pull" in cmd_str:
            result.stdout = "Updating abc1234..def5678"
        elif "pip" in cmd_str:
            result.stdout = "Successfully installed souschef"
        elif "log" in cmd_str and "--format=%s" in cmd_str:
            result.stdout = "fix: a bug\nfeat: a feature"
        else:
            result.stdout = ""
        return result

    with patch("souschef.update.subprocess.run", side_effect=mock_run):
        result = apply_update(root)

    assert result["status"] == "updated"
    assert result["previous"] == "abc1234"
    assert result["current"] == "def5678"
    assert len(result["changes"]) == 2


def test_apply_update_dirty_tree():
    from souschef.update import apply_update
    root = get_repo_root()

    def mock_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        cmd_str = " ".join(str(c) for c in cmd)
        if "status --porcelain" in cmd_str:
            result.stdout = " M some_file.py"
        else:
            result.stdout = ""
        return result

    with patch("souschef.update.subprocess.run", side_effect=mock_run):
        result = apply_update(root)

    assert result["status"] == "error"
    assert "uncommitted" in result["error"]


def test_apply_update_pull_fails():
    from souschef.update import apply_update
    root = get_repo_root()

    def mock_run(cmd, **kwargs):
        result = MagicMock()
        result.stderr = ""
        cmd_str = " ".join(str(c) for c in cmd)
        if "status --porcelain" in cmd_str:
            result.returncode = 0
            result.stdout = ""
        elif "rev-parse HEAD" in cmd_str:
            result.returncode = 0
            result.stdout = "abc1234567890"
        elif "pull" in cmd_str:
            result.returncode = 1
            result.stderr = "error: merge conflict"
            result.stdout = ""
        else:
            result.returncode = 0
            result.stdout = ""
        return result

    with patch("souschef.update.subprocess.run", side_effect=mock_run):
        result = apply_update(root)

    assert result["status"] == "error"
    assert "Pull failed" in result["error"]


def test_apply_update_pip_fails():
    from souschef.update import apply_update
    root = get_repo_root()
    call_count = {"n": 0}

    def mock_run(cmd, **kwargs):
        result = MagicMock()
        result.stderr = ""
        cmd_str = " ".join(str(c) for c in cmd)
        if "status --porcelain" in cmd_str:
            result.returncode = 0
            result.stdout = ""
        elif "rev-parse HEAD" in cmd_str:
            call_count["n"] += 1
            result.returncode = 0
            result.stdout = "abc1234567890" if call_count["n"] == 1 else "def5678901234"
        elif "pull" in cmd_str:
            result.returncode = 0
            result.stdout = "Updating"
        elif "pip" in cmd_str:
            result.returncode = 1
            result.stderr = "ERROR: could not install"
            result.stdout = ""
        else:
            result.returncode = 0
            result.stdout = ""
        return result

    with patch("souschef.update.subprocess.run", side_effect=mock_run):
        result = apply_update(root)

    assert result["status"] == "error"
    assert "Install failed" in result["error"]


def test_apply_update_already_up_to_date():
    from souschef.update import apply_update
    root = get_repo_root()

    def mock_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        cmd_str = " ".join(str(c) for c in cmd)
        if "status --porcelain" in cmd_str:
            result.stdout = ""
        elif "rev-parse HEAD" in cmd_str:
            result.stdout = "abc1234567890"
        elif "pull" in cmd_str:
            result.stdout = "Already up to date."
        else:
            result.stdout = ""
        return result

    with patch("souschef.update.subprocess.run", side_effect=mock_run):
        result = apply_update(root)

    assert result["status"] == "up_to_date"
    assert result["version"] == "abc1234"
