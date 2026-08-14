"""Context briefing assembly.

`bora context` prints the recommended files for orienting a fresh model
session. Optional token budget truncates by dropping less-essential files
first.

We use a rough character-to-token estimate (4 chars per token) instead of
a real tokenizer to avoid a dependency on tiktoken or similar. The estimate
is conservative — actual token counts will usually be smaller.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from .paths import (
    AGENTS_FILE,
    project_file,
    project_tickets_dir,
    requirements_file,
    status_file,
)
from .ticket import load_all_tickets

CHARS_PER_TOKEN = 4  # rough estimate; favors safety


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def _read_if_exists(path: Path) -> Optional[str]:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def _label_for(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return path.name


def _append_if_exists(
    sections: list[tuple[str, str]],
    root: Path,
    path: Path,
    label: Optional[str] = None,
) -> None:
    content = _read_if_exists(path)
    if content is None:
        return
    sections.append((label or _label_for(root, path), content))


def assemble_context(root: Path, project_path: str, budget: Optional[int] = None) -> str:
    """Assemble briefing content for one hierarchical project.

    Order of inclusion (highest priority first):
      1. AGENTS.md (repo root)
      2. dated project briefing (discovered)
      3. dated Requirements (if exists)
      4. Status.md (if exists)
      5. In-progress tickets, then blocked tickets, in that project's tickets/

    Does not read other `docs/ai/<other>/` trees.

    If a budget is given, we include files in order until the budget is
    exhausted, then stop. We always include AGENTS.md regardless of budget
    since omitting it defeats the purpose.
    """
    sections: list[tuple[str, str]] = []

    _append_if_exists(sections, root, root / AGENTS_FILE, label="AGENTS.md")
    _append_if_exists(sections, root, project_file(root, project_path))
    _append_if_exists(sections, root, requirements_file(root, project_path))
    _append_if_exists(sections, root, status_file(root, project_path))

    tickets = load_all_tickets(project_tickets_dir(root, project_path))
    in_progress = [t for t in tickets if t.status == "in-progress"]
    blocked = [t for t in tickets if t.status == "blocked"]

    def _recency(ticket) -> date:
        return ticket.updated or ticket.created or date.min

    in_progress.sort(key=_recency, reverse=True)
    blocked.sort(key=_recency, reverse=True)

    for t in in_progress + blocked:
        sections.append((_label_for(root, t.path), t.path.read_text(encoding="utf-8")))

    # Apply budget if provided
    if budget is not None:
        kept: list[tuple[str, str]] = []
        used = 0
        for i, (label, content) in enumerate(sections):
            section_text = _format_section(label, content)
            section_tokens = estimate_tokens(section_text)
            # Always include the first section (AGENTS.md) even if it busts the budget.
            if i == 0 or used + section_tokens <= budget:
                kept.append((label, content))
                used += section_tokens
            else:
                # Stop including more files; they'd exceed budget.
                break
        sections = kept

    # Render
    parts = [_format_section(label, content) for label, content in sections]
    return "\n\n".join(parts) + "\n"


def _format_section(label: str, content: str) -> str:
    """Render a section with a clear delimiter so a model can tell files apart."""
    return f"===== {label} =====\n\n{content.rstrip()}"
