"""Ticket parsing, serialization, and querying.

A ticket is a Markdown file with YAML frontmatter delimited by `---` lines,
followed by a Markdown body. We parse the frontmatter into a dict, keep the
body as a string, and provide helpers for the operations the CLI needs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import yaml

FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<frontmatter>.*?)\n---\s*\n(?P<body>.*)\Z",
    re.DOTALL,
)

# Match Markdown checkboxes: `- [ ]`, `- [x]`, `- [X]`. Tolerant to leading whitespace.
CHECKBOX_RE = re.compile(r"^\s*-\s*\[(?P<mark>[ xX])\]\s+(?P<text>.+?)$", re.MULTILINE)


@dataclass
class Subtask:
    """A frontmatter-level subtask. Body checkboxes are tracked separately."""

    id: str
    title: str
    status: str = "todo"


@dataclass
class Ticket:
    """In-memory representation of a ticket file."""

    path: Path
    frontmatter: dict[str, Any]
    body: str

    # ---- accessors keep callers from poking at the dict directly ----

    @property
    def id(self) -> str:
        return self.frontmatter.get("id", "")

    @property
    def title(self) -> str:
        return self.frontmatter.get("title", "")

    @property
    def type(self) -> str:
        return self.frontmatter.get("type", "")

    @property
    def priority(self) -> str:
        return self.frontmatter.get("priority", "")

    @property
    def status(self) -> str:
        return self.frontmatter.get("status", "")

    @property
    def notes(self) -> str:
        return self.frontmatter.get("notes", "") or ""

    @property
    def parent(self) -> Optional[str]:
        val = self.frontmatter.get("parent")
        return val if val else None

    @property
    def depends_on(self) -> list[str]:
        return list(self.frontmatter.get("depends_on") or [])

    @property
    def created(self) -> Optional[date]:
        return _coerce_date(self.frontmatter.get("created"))

    @property
    def updated(self) -> Optional[date]:
        return _coerce_date(self.frontmatter.get("updated"))

    @property
    def closed(self) -> Optional[date]:
        return _coerce_date(self.frontmatter.get("closed"))

    @property
    def subtasks(self) -> list[Subtask]:
        raw = self.frontmatter.get("subtasks") or []
        out: list[Subtask] = []
        for item in raw:
            if isinstance(item, dict) and "id" in item and "title" in item:
                out.append(
                    Subtask(
                        id=str(item["id"]),
                        title=str(item["title"]),
                        status=str(item.get("status", "todo")),
                    )
                )
        return out

    # ---- body-derived data ----

    def checkbox_progress(self) -> tuple[int, int]:
        """Return (checked, total) Markdown checkboxes in the body."""
        checked = 0
        total = 0
        for m in CHECKBOX_RE.finditer(self.body):
            total += 1
            if m.group("mark").lower() == "x":
                checked += 1
        return checked, total

    def subtask_progress(self) -> tuple[int, int]:
        """Return (done, total) frontmatter subtasks."""
        subs = self.subtasks
        if not subs:
            return 0, 0
        done = sum(1 for s in subs if s.status == "done")
        return done, len(subs)

    # ---- mutation helpers (do not write to disk; caller calls save()) ----

    def set_field(self, name: str, value: Any) -> None:
        """Set a frontmatter field. Empty string clears the field."""
        if value == "" or value is None:
            self.frontmatter.pop(name, None)
        else:
            self.frontmatter[name] = value
        self.frontmatter["updated"] = date.today()

    def set_subtask_status(self, subtask_id: str, status: str) -> bool:
        """Update a subtask's status by id. Returns True if found."""
        subs = self.frontmatter.get("subtasks") or []
        for item in subs:
            if isinstance(item, dict) and str(item.get("id")) == subtask_id:
                item["status"] = status
                self.frontmatter["updated"] = date.today()
                return True
        return False

    def append_note(self, text: str, when: Optional[date] = None) -> None:
        """Append a dated entry to the body's Notes section.

        Creates the section if it doesn't exist. We look for `## Notes` as the
        section header — case-sensitive on purpose to avoid surprising users
        who use a different convention elsewhere.
        """
        when = when or date.today()
        entry = f"\n### {when.isoformat()}\n{text.rstrip()}\n"
        if "## Notes" in self.body:
            # Append to end of file (Notes is conventionally the last section).
            self.body = self.body.rstrip() + "\n" + entry
        else:
            self.body = self.body.rstrip() + "\n\n## Notes\n" + entry
        self.frontmatter["updated"] = date.today()

    # ---- serialization ----

    def to_text(self) -> str:
        """Render this ticket back to a Markdown file string.

        We post-process yaml.safe_dump's output for two cosmetic fixes:
          - `None` values render as `null`, which we rewrite to a bare empty
            value (e.g., `closed:`) to match the initial template.
          - Empty lists render as `[]` (flow style) which is fine and matches
            the template; we don't need to touch those.
        """
        fm_text = yaml.safe_dump(
            self.frontmatter,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        ).rstrip()
        # Rewrite trailing `: null` → `:` so empty fields look clean.
        # We use a regex anchored on whole lines to avoid touching the word
        # "null" appearing elsewhere (e.g., inside a string value).
        fm_text = re.sub(r"^([\w-]+):\s*null\s*$", r"\1:", fm_text, flags=re.MULTILINE)
        body = self.body if self.body.startswith("\n") else "\n" + self.body
        return f"---\n{fm_text}\n---{body}"

    def save(self) -> None:
        self.path.write_text(self.to_text(), encoding="utf-8")


# =============================================================================
# Parsing & loading
# =============================================================================


def _coerce_date(value: Any) -> Optional[date]:
    """Be liberal about what counts as a date in frontmatter.

    PyYAML parses ISO date literals to `date` objects automatically, but if a
    user (or model) writes a date as a quoted string, we'll get a str back
    and need to handle that.
    """
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def parse_ticket(path: Path) -> Ticket:
    """Parse a ticket file into a Ticket object.

    Raises ValueError on malformed frontmatter so the caller (typically the
    lint command) can surface a useful error rather than silently producing
    a half-broken Ticket.
    """
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(
            f"{path.name}: missing or malformed YAML frontmatter "
            "(expected `---` delimiters at top of file)"
        )
    fm_text = match.group("frontmatter")
    body = match.group("body")
    try:
        frontmatter = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"{path.name}: invalid YAML frontmatter: {e}") from e
    if not isinstance(frontmatter, dict):
        raise ValueError(
            f"{path.name}: frontmatter must be a YAML mapping, got {type(frontmatter).__name__}"
        )
    return Ticket(path=path, frontmatter=frontmatter, body=body)


def load_all_tickets(tickets_dir: Path) -> list[Ticket]:
    """Load every ticket in a directory. Skips files that fail to parse but
    records nothing — use lint() if you want to surface errors."""
    tickets: list[Ticket] = []
    if not tickets_dir.exists():
        return tickets
    for path in sorted(tickets_dir.glob("*.md")):
        try:
            tickets.append(parse_ticket(path))
        except ValueError:
            continue
    return tickets


def find_ticket(tickets_dir: Path, id_query: str) -> Optional[Ticket]:
    """Find a ticket by id with fuzzy matching.

    Match strategy, in order:
      1. Exact id match.
      2. Filename starts-with match (e.g., "20260425-01" matches today's #01).
      3. Slug suffix match (e.g., "add-user-auth" matches by trailing slug).
      4. Short numeric tail (e.g., "01" matches the most recent ticket whose
         filename ends with -01).

    Returns None if no match or multiple ambiguous matches.
    """
    if not tickets_dir.exists():
        return None
    all_tickets = load_all_tickets(tickets_dir)

    # Exact id match
    for t in all_tickets:
        if t.id == id_query:
            return t

    # Filename prefix match (e.g., "20260425-01")
    prefix_matches = [
        t for t in all_tickets if t.path.stem.startswith(id_query)
    ]
    if len(prefix_matches) == 1:
        return prefix_matches[0]

    # Slug suffix match (e.g., "add-user-auth")
    suffix_matches = [
        t for t in all_tickets if t.path.stem.endswith(f"-{id_query}")
    ]
    if len(suffix_matches) == 1:
        return suffix_matches[0]

    # Short numeric tail (e.g., "01" → match ticket ending in "-01" with the
    # most recent created date among ambiguous matches)
    if id_query.isdigit() or re.fullmatch(r"\d+", id_query):
        padded = id_query.zfill(2)
        tail_matches = [
            t for t in all_tickets
            if re.search(rf"-{padded}-", t.path.stem) or t.path.stem.endswith(f"-{padded}")
        ]
        if len(tail_matches) == 1:
            return tail_matches[0]
        if tail_matches:
            # Prefer the most recently created one when ambiguous.
            tail_matches.sort(
                key=lambda t: t.created or date.min,
                reverse=True,
            )
            return tail_matches[0]

    return None
