"""Project file archiving and creation: bora dev project."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Optional

import yaml

from .paths import DOCS_DIR, PROJECT_JSON, PROJECTS_DIR, TICKETS_DIR, find_project_file
from .ticket import load_all_tickets

_DATE_PREFIX_RE = re.compile(r"^\(\d{4}-\d{2}-\d{2}\)\s")


# ---------------------------------------------------------------------------
# project.json helpers
# ---------------------------------------------------------------------------

def read_project_json(root: Path) -> dict:
    path = root / PROJECT_JSON
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def write_project_json(root: Path, data: dict) -> None:
    path = root / PROJECT_JSON
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

def _load_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        return {}


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:]
    return text


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def _get_completed_tickets(root: Path) -> list:
    tickets_path = root / TICKETS_DIR
    if not tickets_path.exists():
        return []
    completed = []
    for t in load_all_tickets(tickets_path):
        if t.status == "done":
            entry = {"id": t.id, "title": t.title}
            if t.closed:
                entry["closed"] = t.closed.isoformat()
            completed.append(entry)
    return completed


def _get_git_log(root: Path, since_date: Optional[str]) -> str:
    """Return git log since start_date, or last 50 commits. Empty string on failure."""
    try:
        if since_date:
            cmd = ["git", "log", "--oneline", f"--after={since_date}"]
        else:
            cmd = ["git", "log", "--oneline", "-50"]
        result = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return ""


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------

def _archive_project(root: Path, version: str, today: str) -> Optional[Path]:
    """Find and archive the active project file. Returns the archive path or None."""
    existing = find_project_file(root)
    if existing is None:
        return None

    text = existing.read_text(encoding="utf-8")
    fm = _load_frontmatter(text)
    body = _strip_frontmatter(text)

    start_date = str(fm.get("start_date", "")) or None
    completed_tickets = _get_completed_tickets(root)
    git_log = _get_git_log(root, start_date)

    # Merge archival fields into existing frontmatter
    archive_fm = dict(fm)
    archive_fm["status"] = "archived"
    archive_fm["archived_date"] = today
    if version:
        archive_fm["archived_at_version"] = version
    if completed_tickets:
        archive_fm["completed_tickets"] = completed_tickets
    if git_log:
        archive_fm["git_log"] = git_log

    archived_text = "---\n" + yaml.dump(archive_fm, default_flow_style=False, allow_unicode=True) + "---\n" + body

    # Determine archive filename — prepend date only if not already present
    filename = existing.name
    if not _DATE_PREFIX_RE.match(filename):
        filename = f"({today}) {filename}"

    # Write to Projects/, handling filename collisions
    projects_dir = root / PROJECTS_DIR
    projects_dir.mkdir(parents=True, exist_ok=True)
    dest = projects_dir / filename
    n = 1
    stem = dest.stem  # e.g. "(2026-07-01) Project"
    while dest.exists():
        dest = projects_dir / f"{stem} ({n}).md"
        n += 1

    existing.write_text(archived_text, encoding="utf-8")
    existing.rename(dest)
    return dest


# ---------------------------------------------------------------------------
# New project file
# ---------------------------------------------------------------------------

def _new_project_content(version: str, description: str, today: str) -> str:
    fm = {
        "version": version,
        "description": description,
        "status": "open",
        "start_date": today,
        "last_reviewed": today,
        "focus": "",
    }
    frontmatter = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return (
        f"---\n{frontmatter}---\n\n"
        "# Project\n\n"
        "## Background\n\n"
        "What is this project? Why does it exist? What's the context a stranger\n"
        "would need to understand the rest of this document?\n\n"
        "## Goals\n\n"
        "What are we trying to accomplish? List the top-level outcomes.\n\n"
        "- Goal 1\n"
        "- Goal 2\n\n"
        "## Non-goals\n\n"
        "What are we explicitly *not* doing? Naming this saves arguments later.\n\n"
        "- Non-goal 1\n\n"
        "## Target users\n\n"
        "Who is this for? What do they need? What do they already know?\n\n"
        "## User stories\n\n"
        "The concrete scenarios this product supports.\n\n"
        "- As a [user type], I want to [action], so that [outcome].\n\n"
        "## Constraints\n\n"
        "Technical, business, or practical constraints that shape the design.\n\n"
        "- Constraint 1\n\n"
        "## Success criteria\n\n"
        "How will we know this project is done — or at least working?\n\n"
        "- Criterion 1\n"
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def archive_and_create(root: Path, version: str, description: str) -> tuple:
    """Archive the active project file and create a new one.

    Returns (archived_path_or_None, new_project_path).
    """
    today = date.today().isoformat()

    archived_path = _archive_project(root, version, today)

    new_filename = f"({today}) Project.md"
    new_path = root / DOCS_DIR / new_filename
    new_path.write_text(_new_project_content(version, description, today), encoding="utf-8")

    proj_data = read_project_json(root)
    proj_data["active"] = new_filename
    proj_data["version"] = version
    write_project_json(root, proj_data)

    return archived_path, new_path
