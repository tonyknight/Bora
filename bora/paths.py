"""Path resolution and shared constants."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

# Directory layout (relative to repo root)
PROFILE_FILE = ".bora/profile.json"
PROJECT_JSON = ".bora/project.json"
DOCS_DIR = "docs/ai"
TICKETS_DIR = "docs/ai/tickets"
PROJECTS_DIR = "docs/ai/Projects"
PROJECT_FILE = "docs/ai/Project.md"
ARCHITECTURE_FILE = "docs/ai/Architecture.md"
TASKS_FILE = "docs/ai/Tasks.md"
AGENTS_FILE = "AGENTS.md"

_DATE_PREFIX_RE = re.compile(r"^\(\d{4}-\d{2}-\d{2}\) Project\.md$")

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


def find_project_file(root: Path) -> Optional[Path]:
    """Return the active Project.md path, or None if none exists.

    Resolution order:
      1. .bora/project.json  → "active" field
      2. Scan docs/ai/ for (YYYY-MM-DD) Project.md — take the latest by date
      3. Plain docs/ai/Project.md (pre-0.3.5 fallback)
    """
    proj_json = root / PROJECT_JSON
    if proj_json.exists():
        try:
            data = json.loads(proj_json.read_text(encoding="utf-8"))
            active = data.get("active")
            if active:
                candidate = root / DOCS_DIR / active
                if candidate.exists():
                    return candidate
        except (json.JSONDecodeError, OSError):
            pass

    docs = root / DOCS_DIR
    if docs.exists():
        candidates = [f for f in docs.iterdir() if f.is_file() and _DATE_PREFIX_RE.match(f.name)]
        if candidates:
            return max(candidates, key=lambda f: f.name)

    plain = root / PROJECT_FILE
    if plain.exists():
        return plain

    return None
