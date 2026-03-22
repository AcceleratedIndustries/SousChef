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

**Error cases (all exit code 1):**
- No git repo found: `{"status": "error", "error": "Not a git repository"}`
- No network / fetch fails: `{"status": "error", "error": "Could not reach remote"}`
- Dirty working tree: still reports update status (doesn't block check)

### `souschef update apply`

Pulls latest from `origin/main` and reinstalls the package.

**Steps:**
1. Check for dirty tracked files via `git status --porcelain`. If any, abort with error.
2. Record current HEAD SHA
3. `git pull origin main` (this fetches internally — no separate fetch needed)
4. `sys.executable -m pip install -e .` (from repo root)
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
- Dirty working tree (any modified tracked files): `{"status": "error", "error": "Working tree has uncommitted changes"}` (exit code 1)
- Pull fails: `{"status": "error", "error": "Pull failed: <details>"}` (exit code 1)
- pip install fails: `{"status": "error", "error": "Install failed: <details>"}` (exit code 1)

### ~~`souschef update install`~~ — Removed

First-time setup is a bootstrap problem: you can't run `souschef` before it's installed. The canonical first-time setup path is documented in CLAUDE.md as manual `git clone` + `pip install` steps. Claude guides Georgayne through this if `souschef` is not found.

## Repo Root Discovery

The update commands need to find the git repo root. Since SousChef is installed as an editable package, resolve from the package's `__file__` path:

```python
# In src/souschef/update.py:
from pathlib import Path
repo_root = Path(__file__).resolve().parent.parent.parent
# update.py → souschef/ → src/ → repo root
```

This depth (3 parents) is correct for any file at `src/souschef/*.py`. Verify by checking that `repo_root / ".git"` exists.

If `.git` is not found, the package wasn't installed from a git clone — report an error.

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

**Note:** `souschef update install` does not exist — it's a bootstrap problem. These manual steps are the canonical first-time setup path.
```

## Implementation Details

### New files
- `src/souschef/cli/update.py` — Typer app with `check` and `apply` commands
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
- `git log HEAD..origin/main --format=%s` — commit message subjects only (no SHA prefix) for changelog
- `git pull origin main` — apply update
- `git clone <url> <path>` — first-time install (manual, not via CLI)

### pip operations

Use `subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], cwd=repo_root)` for installation. Using `sys.executable` ensures pip runs in the correct Python environment, avoiding issues where `pip` on PATH points to a different Python (common on macOS).

### Version representation

Version is the short git SHA (first 7 characters of HEAD). No semver — git SHAs are unambiguous and require zero maintenance. The `__version__` in `__init__.py` is informational only.

## What's Out of Scope

- Semver / release tagging (YAGNI for two users)
- Rollback capability (git revert is available manually if needed)
- Auto-apply without user consent
- Branch selection (always `origin/main`)
- GitHub API version checking (future enhancement when moving away from git-based updates)
