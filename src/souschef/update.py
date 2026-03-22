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
        return True
    return len(result.stdout.strip()) > 0


def check_for_updates(repo_root: Path) -> dict[str, Any]:
    """Fetch from origin and compare local HEAD vs origin/main."""
    fetch = _git(repo_root, "fetch", "origin", "main")
    if fetch.returncode != 0:
        return {"status": "error", "error": f"Could not reach remote: {fetch.stderr.strip()}"}

    local = _git(repo_root, "rev-parse", "HEAD")
    remote = _git(repo_root, "rev-parse", "origin/main")

    if local.returncode != 0 or remote.returncode != 0:
        return {"status": "error", "error": "Could not determine versions"}

    local_sha = local.stdout.strip()
    remote_sha = remote.stdout.strip()

    if local_sha == remote_sha:
        return {"status": "up_to_date", "version": local_sha[:7]}

    count_result = _git(repo_root, "rev-list", f"HEAD..origin/main", "--count")
    commits_behind = int(count_result.stdout.strip()) if count_result.returncode == 0 else 0

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
    """Pull latest from origin/main and reinstall the package."""
    if is_working_tree_dirty(repo_root):
        return {"status": "error", "error": "Working tree has uncommitted changes"}

    old_sha = _git(repo_root, "rev-parse", "HEAD").stdout.strip()

    pull = _git(repo_root, "pull", "origin", "main")
    if pull.returncode != 0:
        return {"status": "error", "error": f"Pull failed: {pull.stderr.strip()}"}

    new_sha = _git(repo_root, "rev-parse", "HEAD").stdout.strip()

    if old_sha == new_sha:
        return {"status": "up_to_date", "version": new_sha[:7]}

    pip_result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", "."],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if pip_result.returncode != 0:
        return {"status": "error", "error": f"Install failed: {pip_result.stderr.strip()}"}

    log_result = _git(repo_root, "log", f"{old_sha}..{new_sha}", "--format=%s")
    changes = [line for line in log_result.stdout.strip().splitlines() if line] if log_result.returncode == 0 else []

    return {
        "status": "updated",
        "previous": old_sha[:7],
        "current": new_sha[:7],
        "changes": changes,
    }
