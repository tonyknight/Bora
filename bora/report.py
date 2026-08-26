"""Assemble a project's Completion document from per-ticket fragments.

Unlike `Status.md`, the result is a draft a human edits — re-running this
without `--force` never overwrites an existing Completion document (Bora
0.8.0 Requirements §13). No network I/O.
"""

from __future__ import annotations

import difflib
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from .paths import (
    dated_filename,
    parse_project_path,
    project_dir,
    project_name,
    project_tickets_dir,
    requirements_file,
)
from .routing import briefing_frontmatter
from .ticket import (
    Ticket,
    completion_report_fields,
    extract_completion_report_section,
    load_all_tickets,
)

_H2_RE = re.compile(r"^## ", re.MULTILINE)
_RANGE_RE = re.compile(r"Range:\s*`([0-9a-fA-F]+)\.\.([0-9a-fA-F]+)`")
_ACCEPTANCE_HEADER = "## Acceptance criteria"
_CHECKLIST_ITEM_RE = re.compile(r"^-\s*\[[ xX]\]\s*(.+)$", re.MULTILINE)


@dataclass
class ReportBuildResult:
    path: Path
    written: bool
    diff_path: Optional[Path] = None
    diff_text: Optional[str] = None


def _extract_section(text: str, header: str) -> Optional[str]:
    """Return the body under an H2 ``header``, or None if absent.

    Anchored to the start of a line (`re.escape(header)` at line start) so
    prose that merely *mentions* the header text — e.g. a Requirements
    document discussing "the `## Non-goals` section" before the real
    heading, exactly the false positive ticket 06 found and fixed for
    ticket bodies — is never mistaken for the actual section.
    """
    match = re.search(rf"^{re.escape(header)}[ \t]*$", text, re.MULTILINE)
    if match is None:
        return None
    rest = text[match.end() :]
    nxt = _H2_RE.search(rest)
    end = match.end() + nxt.start() if nxt else len(text)
    return text[match.end() : end].strip()


def _slugify(project_path: str) -> str:
    text = project_path.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _execute_branch(frontmatter: dict, project_path: str) -> str:
    origin = frontmatter.get("origin_branch") or "main"
    if frontmatter.get("worktree") is True:
        return f"bora/{_slugify(project_path)}"
    return origin


def _git_diff_files(root: Path, start: str, end: str) -> Optional[list[str]]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{start}~1..{end}"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _review_range(body: str) -> Optional[tuple[str, str]]:
    match = _RANGE_RE.search(body)
    if match is None:
        return None
    return match.group(1), match.group(2)


def _acceptance_criteria(body: str) -> list[str]:
    section = _extract_section(body, _ACCEPTANCE_HEADER)
    if section is None:
        return []
    return [m.strip() for m in _CHECKLIST_ITEM_RE.findall(section)]


def _ticket_section(root: Path, ticket: Ticket) -> tuple[str, Optional[str]]:
    """Return (markdown for this ticket's Completion section, errors text or None)."""
    body = ticket.body
    completion = extract_completion_report_section(body)
    lines = [f"### {ticket.id} — {ticket.title}", ""]

    if completion is None:
        lines.append("_Not recorded — this ticket predates the completion-report template._")
        lines.append("")
        return "\n".join(lines), None

    fields = completion_report_fields(completion)
    outcome = fields.get("Outcome", "").strip() or "(not recorded)"
    files_prose = fields.get("Files", "").strip()
    errors = fields.get("Errors", "").strip()
    verify = fields.get("Verify", "").strip() or "(not recorded)"

    lines.append(f"- **Outcome:** {outcome}")

    range_pair = _review_range(body)
    if range_pair is not None:
        git_files = _git_diff_files(root, *range_pair)
        prose_set = {f.strip() for f in files_prose.split(",") if f.strip()}
        if git_files is not None:
            git_set = set(git_files)
            if prose_set == git_set:
                lines.append(f"- **Files:** {files_prose or '(none)'}")
            else:
                lines.append(
                    f"- **Files (mismatch):** prose says `{files_prose or '(none)'}`; "
                    f"git says `{', '.join(sorted(git_set)) or '(none)'}`"
                )
        else:
            lines.append(f"- **Files:** {files_prose or '(none)'}")
    else:
        lines.append(f"- **Files:** {files_prose or '(not recorded)'}")

    lines.append(f"- **Errors:** {errors or 'none'}")
    lines.append(f"- **Verify:** {verify}")
    lines.append("")

    errors_out = errors if errors and errors.strip().lower() != "none" else None
    return "\n".join(lines), errors_out


def _testing_guide_entry(ticket: Ticket) -> str:
    criteria = _acceptance_criteria(ticket.body)
    lines = [f"### {ticket.id} — {ticket.title}", ""]
    if not criteria:
        lines.append("_No acceptance criteria recorded to derive a walkthrough from._")
    else:
        for item in criteria:
            lines.append(f"- Try: {item}")
    lines.append("")
    return "\n".join(lines)


def build_completion_report(
    root: Path,
    project_path: str,
    *,
    force: bool = False,
) -> ReportBuildResult:
    segments = parse_project_path(project_path)
    name = project_name(segments)
    directory = project_dir(root, project_path)
    today = date.today()
    completion_path = directory / dated_filename(today, f"{name} Completion")

    briefing_fm = briefing_frontmatter(root, project_path)
    origin_branch = briefing_fm.get("origin_branch") or "main"
    execute_branch = _execute_branch(briefing_fm, project_path)
    focus = briefing_fm.get("focus") or ""

    reqs_path = requirements_file(root, project_path)
    reqs_text = reqs_path.read_text(encoding="utf-8") if reqs_path.is_file() else ""
    testing_section = _extract_section(reqs_text, "## Testing requirements") or ""
    non_goals_section = _extract_section(reqs_text, "## Non-goals") or ""

    verify_match = re.search(r"\*\*`([^`]+)`\*\*", testing_section)
    verify_command = verify_match.group(1) if verify_match else "(not named in Requirements)"

    tickets = sorted(load_all_tickets(project_tickets_dir(root, project_path)), key=lambda t: t.id)

    ticket_sections: list[str] = []
    error_lines: list[str] = []
    testing_entries: list[str] = []
    blocked_titles: list[str] = []
    for ticket in tickets:
        section, error_text = _ticket_section(root, ticket)
        ticket_sections.append(section)
        if error_text:
            error_lines.append(f"- **{ticket.id}**: {error_text}")
        testing_entries.append(_testing_guide_entry(ticket))
        if ticket.frontmatter.get("status") == "blocked":
            blocked_titles.append(f"- {ticket.id}: {ticket.title}")

    doc = f"""---
hierarchy:
{chr(10).join(f'- {s}' for s in segments)}
last_reviewed: {today.isoformat()}
status: complete
origin_branch: {origin_branch}
execute_branch: {execute_branch}
---

# {name} Completion

Focus: {focus or '(not set)'}

Verify command (Requirements *Testing requirements*): **`{verify_command}`**

---

## Tickets

{chr(10).join(ticket_sections)}
---

## Errors and deviations

{chr(10).join(error_lines) if error_lines else "None recorded."}

---

## Testing guide for human testers

Run `{verify_command}` first and confirm it passes, then walk through each
ticket below by hand.

{chr(10).join(testing_entries)}
---

## Backlog

{non_goals_section if non_goals_section else "(Requirements Non-goals section is empty.)"}

{chr(10).join(blocked_titles) if blocked_titles else ""}
"""

    if completion_path.exists() and not force:
        existing = completion_path.read_text(encoding="utf-8")
        diff_path = completion_path.with_suffix(completion_path.suffix + ".new")
        diff_path.write_text(doc, encoding="utf-8")
        diff = "\n".join(
            difflib.unified_diff(
                existing.splitlines(),
                doc.splitlines(),
                fromfile=str(completion_path.name),
                tofile=str(diff_path.name),
                lineterm="",
            )
        )
        return ReportBuildResult(path=completion_path, written=False, diff_path=diff_path, diff_text=diff)

    completion_path.parent.mkdir(parents=True, exist_ok=True)
    completion_path.write_text(doc, encoding="utf-8")
    return ReportBuildResult(path=completion_path, written=True, diff_path=None)
