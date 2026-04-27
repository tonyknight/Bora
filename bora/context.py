"""Context briefing assembly.

`bora context` prints the recommended files for orienting a fresh model
session. Optional token budget truncates by dropping less-essential files
first.

We use a rough character-to-token estimate (4 chars per token) instead of
a real tokenizer to avoid a dependency on tiktoken or similar. The estimate
is conservative — actual token counts will usually be smaller.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .paths import AGENTS_FILE, ARCHITECTURE_FILE, PROJECT_FILE, TASKS_FILE
from .ticket import load_all_tickets

CHARS_PER_TOKEN = 4  # rough estimate; favors safety


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def _read_if_exists(path: Path) -> Optional[str]:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def assemble_context(root: Path, budget: Optional[int] = None) -> str:
    """Assemble briefing content.

    Order of inclusion (highest priority first):
      1. AGENTS.md
      2. Project.md
      3. Architecture.md
      4. Tasks.md
      5. In-progress tickets (most recently updated first)
      6. Blocked tickets

    If a budget is given, we include files in order until the budget is
    exhausted, then stop. We always include AGENTS.md regardless of budget
    since omitting it defeats the purpose.
    """
    sections: list[tuple[str, str]] = []

    for label, rel_path in [
        ("AGENTS.md", AGENTS_FILE),
        ("docs/ai/Project.md", PROJECT_FILE),
        ("docs/ai/Architecture.md", ARCHITECTURE_FILE),
        ("docs/ai/Tasks.md", TASKS_FILE),
    ]:
        content = _read_if_exists(root / rel_path)
        if content is not None:
            sections.append((label, content))

    # Active tickets
    tickets_dir = root / "docs/ai/tickets"
    active_tickets = [
        t for t in load_all_tickets(tickets_dir)
        if t.status in {"in-progress", "blocked"}
    ]
    active_tickets.sort(
        key=lambda t: (t.updated or t.created or __import__("datetime").date.min),
        reverse=True,
    )
    for t in active_tickets:
        try:
            rel = t.path.relative_to(root)
        except ValueError:
            rel = t.path
        sections.append((str(rel), t.path.read_text(encoding="utf-8")))

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
