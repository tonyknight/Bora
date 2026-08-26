"""Frontmatter and cross-reference validation.

Models occasionally produce invalid YAML, misspell status values, or
reference ticket ids that don't exist. The linter catches these before
they cause confusion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .paths import (
    REQUIRED_FIELDS,
    VALID_PRIORITIES,
    VALID_STATUSES,
    VALID_SUBTASK_STATUSES,
    VALID_TYPES,
)
from .plan import VALID_PLAN_STATUSES, extract_plan_section, parse_plan_tasks
from .ticket import Ticket, load_all_tickets, parse_ticket


@dataclass
class LintIssue:
    """One thing wrong with one file."""

    path: Path
    severity: str  # "error" | "warning"
    message: str

    def format(self, root: Path) -> str:
        try:
            rel = self.path.relative_to(root)
        except ValueError:
            rel = self.path
        return f"  [{self.severity}] {rel}: {self.message}"


COMPLETION_REPORT_HEADER = "## Completion report"
_H2_RE = re.compile(r"^## ", re.MULTILINE)
_COMPLETION_FIELD_RE = re.compile(
    r"-\s*\*\*(Outcome|Files|Errors|Verify):\*\*\s*(.*)$", re.MULTILINE
)


def _completion_report_section(body: str) -> Optional[str]:
    """Return the `## Completion report` section text, or None if absent."""
    idx = body.find(COMPLETION_REPORT_HEADER)
    if idx < 0:
        return None
    rest = body[idx + len(COMPLETION_REPORT_HEADER) :]
    nxt = _H2_RE.search(rest)
    end = idx + len(COMPLETION_REPORT_HEADER) + nxt.start() if nxt else len(body)
    return body[idx:end]


def _completion_report_is_filled(section: str) -> bool:
    fields = dict(_COMPLETION_FIELD_RE.findall(section))
    if len(fields) < 4:
        return False
    return all(value.strip() for value in fields.values())


def lint_ticket(ticket: Ticket, known_ids: set[str]) -> list[LintIssue]:
    """Validate one ticket. `known_ids` is the set of all ticket ids in the
    project, used to validate parent and depends_on references."""
    issues: list[LintIssue] = []
    fm = ticket.frontmatter
    p = ticket.path

    # Required fields
    for field_name in REQUIRED_FIELDS:
        if field_name not in fm or fm[field_name] in (None, ""):
            issues.append(LintIssue(p, "error", f"missing required field: {field_name}"))

    # Enumerated values — only check if present, since missing is already reported
    if fm.get("type") and fm["type"] not in VALID_TYPES:
        issues.append(LintIssue(
            p, "error",
            f"invalid type: {fm['type']!r} (expected one of {sorted(VALID_TYPES)})"
        ))
    if fm.get("priority") and fm["priority"] not in VALID_PRIORITIES:
        issues.append(LintIssue(
            p, "error",
            f"invalid priority: {fm['priority']!r} (expected one of {sorted(VALID_PRIORITIES)})"
        ))
    if fm.get("status") and fm["status"] not in VALID_STATUSES:
        issues.append(LintIssue(
            p, "error",
            f"invalid status: {fm['status']!r} (expected one of {sorted(VALID_STATUSES)})"
        ))

    # id should match the filename stem
    if fm.get("id") and fm["id"] != p.stem:
        issues.append(LintIssue(
            p, "warning",
            f"id {fm['id']!r} does not match filename stem {p.stem!r}"
        ))

    # done tickets should have a closed date
    if fm.get("status") == "done" and not fm.get("closed"):
        issues.append(LintIssue(
            p, "warning",
            "status is 'done' but closed date is empty"
        ))

    # done tickets should have a filled Completion report (0.8.0)
    if fm.get("status") == "done":
        section = _completion_report_section(ticket.body)
        if section is None:
            issues.append(LintIssue(
                p, "warning",
                "status is 'done' but has no ## Completion report section (legacy ticket)"
            ))
        elif not _completion_report_is_filled(section):
            issues.append(LintIssue(
                p, "error",
                "status is 'done' but ## Completion report is not filled in"
            ))

    # Non-done tickets should not have a closed date
    if fm.get("status") and fm.get("status") != "done" and fm.get("closed"):
        issues.append(LintIssue(
            p, "warning",
            f"status is {fm['status']!r} but closed date is set"
        ))

    # parent must reference an existing ticket
    parent = fm.get("parent")
    if parent and parent not in known_ids:
        issues.append(LintIssue(
            p, "error",
            f"parent references unknown ticket: {parent!r}"
        ))

    # depends_on must all reference existing tickets
    for dep in (fm.get("depends_on") or []):
        if dep not in known_ids:
            issues.append(LintIssue(
                p, "error",
                f"depends_on references unknown ticket: {dep!r}"
            ))

    # Subtasks must be well-formed
    subs = fm.get("subtasks") or []
    if not isinstance(subs, list):
        issues.append(LintIssue(p, "error", "subtasks must be a list"))
    else:
        seen_ids: set[str] = set()
        for i, sub in enumerate(subs):
            if not isinstance(sub, dict):
                issues.append(LintIssue(p, "error", f"subtask #{i} is not a mapping"))
                continue
            sub_id = sub.get("id")
            if not sub_id:
                issues.append(LintIssue(p, "error", f"subtask #{i} missing id"))
            elif sub_id in seen_ids:
                issues.append(LintIssue(p, "error", f"duplicate subtask id: {sub_id!r}"))
            else:
                seen_ids.add(sub_id)
            if not sub.get("title"):
                issues.append(LintIssue(p, "error", f"subtask #{i} missing title"))
            sub_status = sub.get("status", "todo")
            if sub_status not in VALID_SUBTASK_STATUSES:
                issues.append(LintIssue(
                    p, "error",
                    f"subtask #{i} has invalid status: {sub_status!r} "
                    f"(expected one of {sorted(VALID_SUBTASK_STATUSES)})"
                ))

    section = extract_plan_section(ticket.body)
    plan_status = fm.get("plan_status")
    if plan_status not in (None, "") and plan_status not in VALID_PLAN_STATUSES:
        issues.append(LintIssue(
            p, "error",
            f"invalid plan_status: {plan_status!r} "
            f"(expected one of {sorted(VALID_PLAN_STATUSES)})"
        ))

    if section is not None:
        tasks = parse_plan_tasks(section)
        seen_tasks: set[str] = set()
        for task in tasks:
            if task.id in seen_tasks:
                issues.append(LintIssue(p, "error", f"duplicate plan task id: {task.id}"))
            else:
                seen_tasks.add(task.id)
        current = fm.get("current_task") or ""
        if current and current not in seen_tasks:
            issues.append(LintIssue(
                p, "error",
                f"current_task {current!r} is not a task id in ## Implementation plan"
            ))

    if fm.get("status") == "in-progress":
        if section is None:
            issues.append(LintIssue(
                p, "error",
                "status is in-progress but ticket has no ## Implementation plan section"
            ))
        elif not parse_plan_tasks(section):
            issues.append(LintIssue(
                p, "error",
                "status is in-progress but ## Implementation plan has no ### Tnn: tasks"
            ))

    return issues


def lint_all(tickets_dir: Path) -> list[LintIssue]:
    """Lint every ticket in a directory. Also reports parse failures."""
    issues: list[LintIssue] = []

    if not tickets_dir.exists():
        return issues

    # First pass: collect parseable tickets and report parse errors
    tickets: list[Ticket] = []
    for path in sorted(tickets_dir.glob("*.md")):
        try:
            tickets.append(parse_ticket(path))
        except ValueError as e:
            issues.append(LintIssue(path, "error", str(e)))

    # Second pass: validate against the set of known ids
    known_ids = {t.id for t in tickets if t.id}
    for ticket in tickets:
        issues.extend(lint_ticket(ticket, known_ids))

    return issues


def get_blocked_tickets(tickets: list[Ticket]) -> dict[str, list[str]]:
    """For each non-done ticket with depends_on, return the unfinished deps.

    Returns a dict of {ticket_id: [unfinished_dep_ids]}. Only tickets that
    are actually blocked (have at least one unfinished dependency) appear.
    """
    by_id = {t.id: t for t in tickets if t.id}
    blocked: dict[str, list[str]] = {}

    for ticket in tickets:
        if ticket.status == "done" or not ticket.depends_on:
            continue
        unfinished = []
        for dep_id in ticket.depends_on:
            dep = by_id.get(dep_id)
            if dep is None or dep.status != "done":
                unfinished.append(dep_id)
        if unfinished:
            blocked[ticket.id] = unfinished

    return blocked
