# SousChef Auto-Update Feature

## Overview

Add update checking and self-updating capabilities to the SousChef CLI so Georgayne's installation stays current with minimal friction. Claude checks for updates when the SousChef skill is loaded and informs her if one is available.

## Architecture

Git is the update mechanism. The SousChef repo is cloned on Georgayne's machine as an editable pip install. Updates are `git pull && pip install -e .`. Version comparison uses git commit SHAs — local HEAD vs `origin/main`.

```
Will pushes to GitHub → Georgayne's Cowork session → `souschef update check` → git fetch
                                                    → `souschef update apply` → git pull + pip install
```

## CLI Commands

### `souschef update check`

Fetches from origin and compares local HEAD against `origin/main`.

**Output (no update):**
```json
{"status": "up_to_date", "version": "abc1234"}
```

**Output (update available):**
```json
{
  "status": "update_available",
  "current": "abc1234",
  "latest": "def5678",
  "commits_behind": 3,
  "changes": [
    "fix: add User-Agent header to HTTP requests",
    "feat: grocery list export improvements"
  ]
}
```

**Error cases:**
- No git repo found: `{"status": "error", "error": "Not a git repository"}`
- No network / fetch fails: `{"status": "error", "error": "Could not reach remote"}`
- Dirty working tree: still reports update status (doesn't block check)

### `souschef update apply`

Pulls latest from `origin/main` and reinstalls the package.

**Steps:**
1. `git fetch origin main`
2. Record current HEAD SHA
3. `git pull origin main`
4. `pip install -e .` (from repo root)
5. Report what changed (commit messages between old HEAD and new HEAD)

**Output (success):**
```json
{
  "status": "updated",
  "previous": "abc1234",
  "current": "def5678",
  "changes": ["fix: ...", "feat: ..."]
}
```

**Output (already up to date):**
```json
{"status": "up_to_date", "version": "abc1234"}
```

**Error cases:**
- Dirty working tree with conflicts: `{"status": "error", "error": "Working tree has uncommitted changes"}`
- Pull fails: `{"status": "error", "error": "Pull failed: <details>"}`
- pip install fails: `{"status": "error", "error": "Install failed: <details>"}`

### `souschef update install`

First-time setup. Clones the repo and installs the package.

**Steps:**
1. Clone `git@github.com:AcceleratedIndustries/SousChef.git` to `~/SousChef`
2. `pip install -e .` from the cloned directory
3. Report success with install path

**Output:**
```json
{
  "status": "installed",
  "path": "/Users/georgayne/SousChef",
  "version": "abc1234"
}
```

**Error cases:**
- Directory already exists: `{"status": "error", "error": "Directory ~/SousChef already exists"}`
- Clone fails (auth): `{"status": "error", "error": "Clone failed: <details>"}`
- pip install fails: `{"status": "error", "error": "Install failed: <details>"}`

## Repo Root Discovery

The update commands need to find the git repo root. Since SousChef is installed as an editable package, resolve from the package's `__file__` path:

```python
from pathlib import Path
repo_root = Path(__file__).resolve().parent.parent.parent  # src/souschef/__init__.py → repo root
```

Verify by checking that `repo_root / ".git"` exists. If not, the package wasn't installed from a git clone — report an error.

## CLAUDE.md Changes

Add to the top of CLAUDE.md, before existing content:

```markdown
## On Session Start
Run `souschef update check` silently. If an update is available, inform the user:
"A SousChef update is available (N new changes). Say 'update souschef' when you're ready."
If up to date or if the check fails, say nothing.

## First-Time Setup
If the `souschef` command is not found, guide the user through setup:
1. Ensure SSH key is configured for GitHub
2. Run: git clone git@github.com:AcceleratedIndustries/SousChef.git ~/SousChef
3. Run: cd ~/SousChef && pip install -e ".[dev]"
4. Run: souschef db init

Or use the one-liner if souschef is somehow available:
souschef update install
```

## Implementation Details

### New files
- `src/souschef/cli/update.py` — Typer app with `check`, `apply`, `install` commands
- `src/souschef/update.py` — core update logic (repo discovery, git operations, version comparison)
- `tests/test_update.py` — tests for update logic
- `tests/test_cli/test_update_cli.py` — CLI-level tests

### Git operations

Use `subprocess.run` for git commands (not a git library — fewer dependencies). Capture stdout/stderr, parse as needed.

Key git commands used:
- `git fetch origin main` — update remote refs
- `git rev-parse HEAD` — current local SHA
- `git rev-parse origin/main` — latest remote SHA
- `git rev-list HEAD..origin/main --count` — how many commits behind
- `git log HEAD..origin/main --oneline` — commit messages for changelog
- `git pull origin main` — apply update
- `git clone <url> <path>` — first-time install

### pip operations

Use `subprocess.run(["pip", "install", "-e", "."], cwd=repo_root)` for installation.

### Version representation

Version is the short git SHA (first 7 characters of HEAD). No semver — git SHAs are unambiguous and require zero maintenance. The `__version__` in `__init__.py` is informational only.

## What's Out of Scope

- Semver / release tagging (YAGNI for two users)
- Rollback capability (git revert is available manually if needed)
- Auto-apply without user consent
- Branch selection (always `origin/main`)
- GitHub API version checking (future enhancement when moving away from git-based updates)
