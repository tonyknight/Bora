"""Ticket creation: generates the next ID for today and writes the file."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .templates import ticket_template


def slugify(title: str) -> str:
    """Convert a ticket title to a URL-safe slug.

    Lowercase, replace runs of non-alphanumerics with single hyphens, strip
    leading/trailing hyphens, truncate to 50 chars on a word boundary.
    """
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    if len(slug) > 50:
        # Truncate on a hyphen so we don't end mid-word.
        truncated = slug[:50]
        last_hyphen = truncated.rfind("-")
        if last_hyphen > 30:  # Don't cut too aggressively
            truncated = truncated[:last_hyphen]
        slug = truncated
    return slug or "untitled"


def next_ticket_id(tickets_dir: Path, title: str, when: date | None = None) -> str:
    """Generate the next ticket ID for today.

    Format: YYYYMMDD-NN-slug, where NN is the next available 2-digit number
    for today, starting at 01. We scan the directory rather than maintaining
    a counter so the script is stateless — losing state to a git checkout or
    a fresh clone wouldn't break ID generation.
    """
    when = when or date.today()
    date_prefix = when.strftime("%Y%m%d")
    slug = slugify(title)

    next_n = 1
    if tickets_dir.exists():
        pattern = re.compile(rf"^{date_prefix}-(\d+)-")
        used: set[int] = set()
        for path in tickets_dir.glob(f"{date_prefix}-*.md"):
            m = pattern.match(path.stem)
            if m:
                try:
                    used.add(int(m.group(1)))
                except ValueError:
                    pass
        if used:
            next_n = max(used) + 1

    return f"{date_prefix}-{next_n:02d}-{slug}"


def create_ticket(
    tickets_dir: Path,
    title: str,
    ticket_type: str,
    priority: str,
    parent: str = "",
) -> Path:
    """Create a new ticket file. Returns the path."""
    tickets_dir.mkdir(parents=True, exist_ok=True)
    ticket_id = next_ticket_id(tickets_dir, title)
    path = tickets_dir / f"{ticket_id}.md"
    if path.exists():
        # Should be unreachable given next_ticket_id logic, but guard anyway.
        raise FileExistsError(f"Ticket already exists: {path}")
    content = ticket_template(
        ticket_id=ticket_id,
        title=title,
        ticket_type=ticket_type,
        priority=priority,
        parent=parent,
    )
    path.write_text(content, encoding="utf-8")
    return path
