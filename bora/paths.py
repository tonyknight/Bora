"""Path resolution and shared constants."""

from __future__ import annotations

import csv
import io
import re
from datetime import date
from pathlib import Path
from typing import Optional

# Directory layout (relative to repo root)
PROFILE_FILE = ".bora/profile.json"
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


class ProjectPathError(ValueError):
    """Invalid hierarchical project path."""


def split_trailing_tags(raw: str) -> tuple[str, str | None]:
    text = raw.strip()
    m = re.match(r"^(.*?)\s*\[(.*)\]\s*$", text)
    if m and "/" in m.group(1):
        return m.group(1).strip(), m.group(2)
    return text, None


def parse_tags(raw: str) -> list[str]:
    text = raw.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    return [item.strip() for item in rows[0] if item.strip()]


def tag_key(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def parse_project_path(raw: str) -> tuple[str, ...]:
    text = raw.strip()
    if (text.startswith('"') and text.endswith('"')) or (
        text.startswith("'") and text.endswith("'")
    ):
        text = text[1:-1]
    if not text:
        raise ProjectPathError("project path is empty")

    prefix_check = text
    if prefix_check.startswith("./") or prefix_check.startswith(".\\"):
        prefix_check = prefix_check[2:]
    normalized_prefix = prefix_check.replace("\\", "/")
    if normalized_prefix == "docs/ai" or normalized_prefix.startswith("docs/ai/"):
        corrected = normalized_prefix[len("docs/ai/") :] if normalized_prefix != "docs/ai" else ""
        raise ProjectPathError(
            f'project_path is relative to docs/ai/. Did you mean "{corrected}"?'
        )

    if text.startswith("/"):
        raise ProjectPathError("project path must not be absolute")
    if "//" in text:
        raise ProjectPathError("project path has empty segments")
    if text.endswith("/"):
        raise ProjectPathError("project path must not have a trailing slash")
    segments = tuple(text.split("/"))
    if len(segments) < 2:
        raise ProjectPathError("project path must have at least two segments (Codebase/Project)")
    for seg in segments:
        if seg.strip() == "":
            raise ProjectPathError("project path has empty or whitespace-only segments")
        if seg in {".", ".."}:
            raise ProjectPathError("project path must not contain . or .. segments")
        if "/" in seg or "\\" in seg:
            raise ProjectPathError("project path segment contains path separators")
    return segments


def project_dir(root: Path, project_path: str) -> Path:
    segments = parse_project_path(project_path)
    return root.joinpath("docs", "ai", *segments)


def project_name(segments: tuple[str, ...]) -> str:
    return segments[-1]


def dated_filename(when: date, name: str, *, requirements: bool = False) -> str:
    suffix = " Requirements.md" if requirements else ".md"
    return f"({when.isoformat()}) {name}{suffix}"


_BRIEFING_RE = re.compile(r"^\(\d{4}-\d{2}-\d{2}\) (.+)\.md$")
_REQUIREMENTS_RE = re.compile(r"^\(\d{4}-\d{2}-\d{2}\) (.+) Requirements\.md$")


def discover_project_file(directory: Path, name: str) -> Optional[Path]:
    if not directory.exists():
        return None
    matches = []
    for p in directory.iterdir():
        if not p.is_file():
            continue
        if p.name.endswith(" Requirements.md"):
            continue
        m = _BRIEFING_RE.match(p.name)
        if m and m.group(1) == name:
            matches.append(p)
    if not matches:
        return None
    return max(matches, key=lambda f: f.name)


def discover_requirements_file(directory: Path, name: str) -> Optional[Path]:
    if not directory.exists():
        return None
    matches = []
    for p in directory.iterdir():
        if not p.is_file():
            continue
        m = _REQUIREMENTS_RE.match(p.name)
        if m and m.group(1) == name:
            matches.append(p)
    if not matches:
        return None
    return max(matches, key=lambda f: f.name)


def project_file(root: Path, project_path: str, *, today: Optional[date] = None) -> Path:
    segments = parse_project_path(project_path)
    name = project_name(segments)
    directory = project_dir(root, project_path)
    found = discover_project_file(directory, name)
    if found is not None:
        return found
    when = today or date.today()
    return directory / dated_filename(when, name)


def requirements_file(root: Path, project_path: str, *, today: Optional[date] = None) -> Path:
    segments = parse_project_path(project_path)
    name = project_name(segments)
    directory = project_dir(root, project_path)
    found = discover_requirements_file(directory, name)
    if found is not None:
        return found
    when = today or date.today()
    return directory / dated_filename(when, name, requirements=True)


def status_file(root: Path, project_path: str) -> Path:
    return project_dir(root, project_path) / "Status.md"


def project_tickets_dir(root: Path, project_path: str) -> Path:
    return project_dir(root, project_path) / "tickets"
