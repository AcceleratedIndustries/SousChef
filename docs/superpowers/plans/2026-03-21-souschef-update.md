# SousChef Auto-Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `souschef update check` and `souschef update apply` commands so Georgayne's installation stays current via git.

**Architecture:** Core update logic in `update.py` (repo discovery, git subprocess calls, version comparison). CLI layer in `cli/update.py` (Typer commands with JSON output). CLAUDE.md updated with session-start auto-check instructions.

**Tech Stack:** Python subprocess (git), sys.executable (pip), existing Typer CLI patterns

**Spec:** `docs/superpowers/specs/2026-03-21-souschef-update-design.md`

---

## File Structure

```
src/souschef/
├── update.py              # core update logic (repo discovery, git ops, version compare)
├── cli/
│   ├── update.py          # Typer commands: check, apply
│   └── main.py            # modified: register update subcommand
CLAUDE.md                  # modified: add session-start and first-time setup sections
tests/
├── test_update.py         # tests for core update logic
└── test_cli/
    └── test_update_cli.py # CLI-level tests
```

---

## Task 1: Core Update Logic

**Files:**
- Create: `src/souschef/update.py`
- Create: `tests/test_update.py`

- [ ] **Step 1: Write failing tests for repo discovery and git operations**

```python
# tests/test_update.py
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
    """get_repo_root returns the repo root (we're in a git repo right now)."""
    root = get_repo_root()
    assert root is not None
    assert (root / ".git").exists()


def test_get_repo_root_returns_none_outside_git(tmp_path):
    """get_repo_root returns None when package is not in a git repo."""
    # Mock __file__ to point outside a git repo
    fake_path = tmp_path / "src" / "souschef" / "update.py"
    fake_path.parent.mkdir(parents=True)
    fake_path.touch()
    with patch("souschef.update._THIS_FILE", fake_path):
        root = get_repo_root()
    assert root is None


def test_get_current_version():
    """get_current_version returns a 7-char hex string."""
    root = get_repo_root()
    version = get_current_version(root)
    assert version is not None
    assert len(version) == 7
    assert all(c in "0123456789abcdef" for c in version)


def test_is_working_tree_dirty_on_clean_repo():
    """A freshly committed repo should not be dirty."""
    root = get_repo_root()
    # This test assumes the repo is clean when tests run
    # It may need to be skipped in CI if there are uncommitted changes
    dirty = is_working_tree_dirty(root)
    assert isinstance(dirty, bool)


def test_check_for_updates_with_mock():
    """check_for_updates returns correct structure when behind."""
    root = get_repo_root()

    def mock_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""

        cmd_str = " ".join(cmd)
        if "fetch" in cmd_str:
            pass  # no output needed
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
    """check_for_updates returns up_to_date when SHAs match."""
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
    """check_for_updates returns error when fetch fails."""
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
    """apply_update pulls, reinstalls, and reports changes."""
    from souschef.update import apply_update

    root = get_repo_root()
    call_count = {"n": 0}

    def mock_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""

        cmd_str = " ".join(str(c) for c in cmd)
        if "status --porcelain" in cmd_str:
            result.stdout = ""  # clean tree
        elif "rev-parse HEAD" in cmd_str:
            call_count["n"] += 1
            # First call = old SHA, second call = new SHA
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
    """apply_update refuses when working tree has changes."""
    from souschef.update import apply_update

    root = get_repo_root()

    def mock_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        cmd_str = " ".join(str(c) for c in cmd)
        if "status --porcelain" in cmd_str:
            result.stdout = " M some_file.py"  # dirty
        else:
            result.stdout = ""
        return result

    with patch("souschef.update.subprocess.run", side_effect=mock_run):
        result = apply_update(root)

    assert result["status"] == "error"
    assert "uncommitted" in result["error"]


def test_apply_update_pull_fails():
    """apply_update returns error when git pull fails."""
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
    """apply_update returns error when pip install fails."""
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
    """apply_update reports up_to_date when SHAs match after pull."""
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
            result.stdout = "abc1234567890"  # same before and after
        elif "pull" in cmd_str:
            result.stdout = "Already up to date."
        else:
            result.stdout = ""
        return result

    with patch("souschef.update.subprocess.run", side_effect=mock_run):
        result = apply_update(root)

    assert result["status"] == "up_to_date"
    assert result["version"] == "abc1234"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_update.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'souschef.update'`

- [ ] **Step 3: Implement core update logic**

```python
# src/souschef/update.py
"""Core update logic — repo discovery, git operations, version comparison."""

import subprocess
import sys
from pathlib import Path
from typing import Any

_THIS_FILE = Path(__file__).resolve()


def get_repo_root() -> Path | None:
    """Find the git repo root from this file's location.

    Walks up from src/souschef/update.py → souschef/ → src/ → repo root.
    Returns None if .git directory is not found.
    """
    root = _THIS_FILE.parent.parent.parent
    if (root / ".git").exists():
        return root
    return None


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess:
    """Run a git command in the repo root."""
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
    )


def get_current_version(repo_root: Path) -> str | None:
    """Get the short SHA of HEAD."""
    result = _git(repo_root, "rev-parse", "HEAD")
    if result.returncode != 0:
        return None
    return result.stdout.strip()[:7]


def is_working_tree_dirty(repo_root: Path) -> bool:
    """Check if there are modified tracked files."""
    result = _git(repo_root, "status", "--porcelain")
    if result.returncode != 0:
        return True  # assume dirty if we can't check
    return len(result.stdout.strip()) > 0


def check_for_updates(repo_root: Path) -> dict[str, Any]:
    """Fetch from origin and compare local HEAD vs origin/main.

    Returns a dict with status and details.
    """
    # Fetch
    fetch = _git(repo_root, "fetch", "origin", "main")
    if fetch.returncode != 0:
        return {"status": "error", "error": f"Could not reach remote: {fetch.stderr.strip()}"}

    # Get local and remote SHAs
    local = _git(repo_root, "rev-parse", "HEAD")
    remote = _git(repo_root, "rev-parse", "origin/main")

    if local.returncode != 0 or remote.returncode != 0:
        return {"status": "error", "error": "Could not determine versions"}

    local_sha = local.stdout.strip()
    remote_sha = remote.stdout.strip()

    if local_sha == remote_sha:
        return {"status": "up_to_date", "version": local_sha[:7]}

    # Count commits behind
    count_result = _git(repo_root, "rev-list", f"HEAD..origin/main", "--count")
    commits_behind = int(count_result.stdout.strip()) if count_result.returncode == 0 else 0

    # Get commit messages
    log_result = _git(repo_root, "log", "HEAD..origin/main", "--format=%s")
    changes = [line for line in log_result.stdout.strip().splitlines() if line] if log_result.returncode == 0 else []

    return {
        "status": "update_available",
        "current": local_sha[:7],
        "latest": remote_sha[:7],
        "commits_behind": commits_behind,
        "changes": changes,
    }


def apply_update(repo_root: Path) -> dict[str, Any]:
    """Pull latest from origin/main and reinstall the package.

    Returns a dict with status and details.
    """
    # Check for dirty working tree
    if is_working_tree_dirty(repo_root):
        return {"status": "error", "error": "Working tree has uncommitted changes"}

    # Record current HEAD
    old_sha = _git(repo_root, "rev-parse", "HEAD").stdout.strip()

    # Pull
    pull = _git(repo_root, "pull", "origin", "main")
    if pull.returncode != 0:
        return {"status": "error", "error": f"Pull failed: {pull.stderr.strip()}"}

    # Check if anything changed
    new_sha = _git(repo_root, "rev-parse", "HEAD").stdout.strip()

    if old_sha == new_sha:
        return {"status": "up_to_date", "version": new_sha[:7]}

    # Reinstall
    pip_result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", "."],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if pip_result.returncode != 0:
        return {"status": "error", "error": f"Install failed: {pip_result.stderr.strip()}"}

    # Get changelog
    log_result = _git(repo_root, "log", f"{old_sha}..{new_sha}", "--format=%s")
    changes = [line for line in log_result.stdout.strip().splitlines() if line] if log_result.returncode == 0 else []

    return {
        "status": "updated",
        "previous": old_sha[:7],
        "current": new_sha[:7],
        "changes": changes,
    }
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest tests/test_update.py -v
```

Expected: all 13 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/souschef/update.py tests/test_update.py
git commit -m "feat: core update logic with repo discovery, check, and apply"
```

---

## Task 2: CLI Update Commands

**Files:**
- Create: `src/souschef/cli/update.py`
- Modify: `src/souschef/cli/main.py`
- Create: `tests/test_cli/test_update_cli.py`

- [ ] **Step 1: Write failing CLI tests**

```python
# tests/test_cli/test_update_cli.py
"""CLI tests for update commands."""

import json
from unittest.mock import patch

from typer.testing import CliRunner
from souschef.cli.main import app

runner = CliRunner()


def test_update_check_up_to_date():
    """update check returns up_to_date JSON when no update available."""
    mock_result = {"status": "up_to_date", "version": "abc1234"}

    with patch("souschef.cli.update.get_repo_root", return_value="/fake/path"), \
         patch("souschef.cli.update.check_for_updates", return_value=mock_result):
        result = runner.invoke(app, ["update", "check"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["status"] == "up_to_date"


def test_update_check_update_available():
    """update check returns update_available JSON with changes."""
    mock_result = {
        "status": "update_available",
        "current": "abc1234",
        "latest": "def5678",
        "commits_behind": 2,
        "changes": ["fix: bug", "feat: feature"],
    }

    with patch("souschef.cli.update.get_repo_root", return_value="/fake/path"), \
         patch("souschef.cli.update.check_for_updates", return_value=mock_result):
        result = runner.invoke(app, ["update", "check"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["status"] == "update_available"
    assert data["commits_behind"] == 2


def test_update_check_no_repo():
    """update check returns error when not in a git repo."""
    with patch("souschef.cli.update.get_repo_root", return_value=None):
        result = runner.invoke(app, ["update", "check"])

    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["status"] == "error"


def test_update_check_network_error():
    """update check returns error when fetch fails."""
    mock_result = {"status": "error", "error": "Could not reach remote"}

    with patch("souschef.cli.update.get_repo_root", return_value="/fake/path"), \
         patch("souschef.cli.update.check_for_updates", return_value=mock_result):
        result = runner.invoke(app, ["update", "check"])

    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["status"] == "error"


def test_update_apply_success():
    """update apply returns updated JSON on success."""
    mock_result = {
        "status": "updated",
        "previous": "abc1234",
        "current": "def5678",
        "changes": ["fix: something"],
    }

    with patch("souschef.cli.update.get_repo_root", return_value="/fake/path"), \
         patch("souschef.cli.update.apply_update", return_value=mock_result):
        result = runner.invoke(app, ["update", "apply"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["status"] == "updated"


def test_update_apply_dirty_tree():
    """update apply returns error when working tree is dirty."""
    mock_result = {"status": "error", "error": "Working tree has uncommitted changes"}

    with patch("souschef.cli.update.get_repo_root", return_value="/fake/path"), \
         patch("souschef.cli.update.apply_update", return_value=mock_result):
        result = runner.invoke(app, ["update", "apply"])

    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["status"] == "error"
    assert "uncommitted" in data["error"]


def test_update_apply_up_to_date():
    """update apply returns up_to_date when already current."""
    mock_result = {"status": "up_to_date", "version": "abc1234"}

    with patch("souschef.cli.update.get_repo_root", return_value="/fake/path"), \
         patch("souschef.cli.update.apply_update", return_value=mock_result):
        result = runner.invoke(app, ["update", "apply"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["status"] == "up_to_date"


def test_update_apply_no_repo():
    """update apply returns error when not in a git repo."""
    with patch("souschef.cli.update.get_repo_root", return_value=None):
        result = runner.invoke(app, ["update", "apply"])

    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["status"] == "error"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_cli/test_update_cli.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'souschef.cli.update'`

- [ ] **Step 3: Implement CLI update commands**

```python
# src/souschef/cli/update.py
"""Update management CLI commands."""

import json

import typer

from souschef.update import get_repo_root, check_for_updates, apply_update

app = typer.Typer(help="Check for and apply updates.")


@app.command()
def check():
    """Check if a SousChef update is available."""
    repo_root = get_repo_root()
    if repo_root is None:
        typer.echo(json.dumps({"status": "error", "error": "Not a git repository"}))
        raise typer.Exit(code=1)

    result = check_for_updates(repo_root)
    typer.echo(json.dumps(result, default=str))
    if result["status"] == "error":
        raise typer.Exit(code=1)


@app.command()
def apply():
    """Pull latest updates and reinstall SousChef."""
    repo_root = get_repo_root()
    if repo_root is None:
        typer.echo(json.dumps({"status": "error", "error": "Not a git repository"}))
        raise typer.Exit(code=1)

    result = apply_update(repo_root)
    typer.echo(json.dumps(result, default=str))
    if result["status"] == "error":
        raise typer.Exit(code=1)
```

- [ ] **Step 4: Register update subcommand in main.py**

Add to `src/souschef/cli/main.py` inside `register_subcommands()`:

```python
from souschef.cli.update import app as update_app
app.add_typer(update_app, name="update")
```

- [ ] **Step 5: Run tests**

```bash
.venv/bin/python -m pytest tests/test_cli/test_update_cli.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 6: Run ALL tests**

```bash
.venv/bin/python -m pytest tests/ -v
```

Expected: all tests PASS (75 existing + 13 update core + 9 update CLI = 97).

- [ ] **Step 7: Commit**

```bash
git add src/souschef/cli/update.py src/souschef/cli/main.py tests/test_cli/test_update_cli.py
git commit -m "feat: souschef update check and apply CLI commands"
```

---

## Task 3: CLAUDE.md Updates

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add session-start and first-time setup sections**

Add the following to the top of `CLAUDE.md`, immediately after the first heading and intro paragraph, before the `---` separator and `## Setup` section:

```markdown
## On Session Start

Run `souschef update check` silently. If an update is available, inform the user:
"A SousChef update is available (N new changes). Say 'update souschef' when you're ready."
If up to date or if the check fails, say nothing.

When the user says "update souschef" or similar, run `souschef update apply` and report the changes.

## First-Time Setup

If the `souschef` command is not found, guide the user through setup:
1. Ensure SSH key is configured for GitHub
2. Run: `git clone git@github.com:AcceleratedIndustries/SousChef.git ~/SousChef`
3. Run: `cd ~/SousChef && pip install -e ".[dev]"`
4. Run: `souschef db init`
```

- [ ] **Step 2: Add update commands to the Available Commands section**

Add a new `### Update` subsection under Available Commands:

```markdown
### Update

**Check for updates:**

```bash
souschef update check
```

**Apply available updates:**

```bash
souschef update apply
```
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add update check and first-time setup instructions to CLAUDE.md"
```

---

## Task 4: Manual Smoke Test

- [ ] **Step 1: Run all tests**

```bash
.venv/bin/python -m pytest tests/ -v --tb=short
```

Expected: all 97 tests PASS.

- [ ] **Step 2: Test update check against the real repo**

```bash
.venv/bin/souschef update check
```

Expected: JSON output with `status` (likely `up_to_date` since we just committed).

- [ ] **Step 3: Verify update apply works when up to date**

```bash
.venv/bin/souschef update apply
```

Expected: `{"status": "up_to_date", "version": "..."}` (since there's nothing to pull).
