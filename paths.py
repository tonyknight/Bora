"""Path resolution and shared constants."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

# Directory layout (relative to repo root)
DOCS_DIR = "docs/ai"
TICKETS_DIR = "docs/ai/tickets"
PROJECT_FILE = "docs/ai/Project.md"
ARCHITECTURE_FILE = "docs/ai/Architecture.md"
TASKS_FILE = "docs/ai/Tasks.md"
AGENTS_FILE = "AGENTS.md"

# Valid frontmatter values
VALID_TYPES = {"feature", "bug", "chore", "spike"}
VALID_PRIORITIES = {"high", "medium", "low"}
VALID_STATUSES = {"todo", "in-progress", "blocked", "done"}
VALID_SUBTASK_STATUSES = {"todo", "in-progress", "done"}

# Required frontmatter fields
REQUIRED_FIELDS = {"id", "title", "type", "priority", "status", "created"}


def find_repo_root(start: Optional[Path] = None) -> Optional[Path]:
    """Walk up from `start` looking for AGENTS.md or .git to identify the repo root.

    Returns None if no root is found. We accept either marker because a project
    may be initialized before being put under git, or the user may want to use
    bora outside of git entirely.
    """
    current = (start or Path.cwd()).resolve()
    for parent in [current, *current.parents]:
        if (parent / AGENTS_FILE).exists() or (parent / ".git").exists():
            return parent
    return None


def require_repo_root() -> Path:
    """Find the repo root or raise a helpful error."""
    root = find_repo_root()
    if root is None:
        raise RuntimeError(
            "Could not find repo root. Run `bora init` first, "
            "or run this command from within an initialized project."
        )
    return root


def tickets_dir(root: Path) -> Path:
    return root / TICKETS_DIR


def docs_dir(root: Path) -> Path:
    return root / DOCS_DIR
