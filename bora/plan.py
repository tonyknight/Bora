"""Parse and mutate the ticket `## Implementation plan` section."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

VALID_PLAN_STATUSES = {"draft", "approved", "in-progress", "done", "blocked"}

PLAN_HEADER = "## Implementation plan"
TASK_HEADING_RE = re.compile(r"^### (T\d{2}):\s*(.+?)\s*$", re.MULTILINE)
# Use [ \t] not \s — \s matches newlines and would swallow the next heading.
STATUS_LINE_RE = re.compile(r"^Status:[ \t]*(.*)$", re.MULTILINE)
CURRENT_TASK_LINE_RE = re.compile(r"^Current task:[ \t]*(.*)$", re.MULTILINE)
DONE_CHECKBOX_RE = re.compile(r"^(\s*-\s*\[)([ xX])(\]\s+done\s*)$", re.MULTILINE)
H2_RE = re.compile(r"^## ", re.MULTILINE)


@dataclass
class PlanTask:
    """One Tnn heading inside the implementation plan."""

    id: str
    title: str
    done: bool
    start: int
    end: int


def extract_plan_section(body: str) -> Optional[str]:
    """Return the `## Implementation plan` section, or None if absent."""
    span = _section_span(body)
    if span is None:
        return None
    start, end = span
    return body[start:end]


def _section_span(body: str) -> Optional[tuple[int, int]]:
    idx = body.find(PLAN_HEADER)
    if idx < 0:
        return None
    # Section runs until the next H2 (not the plan header itself).
    rest = body[idx + len(PLAN_HEADER) :]
    nxt = H2_RE.search(rest)
    end = idx + len(PLAN_HEADER) + nxt.start() if nxt else len(body)
    return idx, end


def parse_plan_tasks(section: str) -> list[PlanTask]:
    """Parse `### T01:` headings and their `- [ ] done` checkboxes."""
    matches = list(TASK_HEADING_RE.finditer(section))
    tasks: list[PlanTask] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(section)
        block = section[start:end]
        done = False
        box = DONE_CHECKBOX_RE.search(block)
        if box:
            done = box.group(2).lower() == "x"
        tasks.append(
            PlanTask(
                id=match.group(1),
                title=match.group(2).strip(),
                done=done,
                start=start,
                end=end,
            )
        )
    return tasks


def set_plan_status_line(body: str, status: str) -> str:
    """Set the `Status:` line inside the implementation plan section."""
    span = _section_span(body)
    if span is None:
        return body
    start, end = span
    section = body[start:end]
    if STATUS_LINE_RE.search(section):
        section = STATUS_LINE_RE.sub(f"Status: {status}", section, count=1)
    else:
        # Insert after the heading line.
        nl = section.find("\n")
        insert_at = nl + 1 if nl >= 0 else len(section)
        section = section[:insert_at] + f"Status: {status}\n" + section[insert_at:]
    return body[:start] + section + body[end:]


def set_current_task_line(body: str, task_id: str) -> str:
    """Set the `Current task:` line inside the implementation plan section."""
    span = _section_span(body)
    if span is None:
        return body
    start, end = span
    section = body[start:end]
    value = task_id or ""
    if CURRENT_TASK_LINE_RE.search(section):
        section = CURRENT_TASK_LINE_RE.sub(f"Current task: {value}", section, count=1)
    else:
        nl = section.find("\n")
        insert_at = nl + 1 if nl >= 0 else len(section)
        section = section[:insert_at] + f"Current task: {value}\n" + section[insert_at:]
    return body[:start] + section + body[end:]


def set_task_checkbox(body: str, task_id: str, *, done: bool) -> str:
    """Check or uncheck a plan task's `done` box and update Current task."""
    span = _section_span(body)
    if span is None:
        raise ValueError("ticket has no ## Implementation plan section")
    start, end = span
    section = body[start:end]
    tasks = parse_plan_tasks(section)
    target = next((t for t in tasks if t.id == task_id), None)
    if target is None:
        raise ValueError(f"no plan task {task_id}")
    block = section[target.start : target.end]
    mark = "x" if done else " "
    new_block, n = DONE_CHECKBOX_RE.subn(
        lambda m: m.group(1) + mark + m.group(3),
        block,
        count=1,
    )
    if n == 0:
        # No checkbox yet — append one.
        new_block = block.rstrip() + f"\n- [{mark}] done\n"
    section = section[: target.start] + new_block + section[target.end :]

    # Re-parse to pick the next unchecked task.
    tasks = parse_plan_tasks(section)
    next_open = next((t.id for t in tasks if not t.done), "")
    if CURRENT_TASK_LINE_RE.search(section):
        section = CURRENT_TASK_LINE_RE.sub(f"Current task: {next_open}", section, count=1)
    else:
        nl = section.find("\n")
        insert_at = nl + 1 if nl >= 0 else len(section)
        section = section[:insert_at] + f"Current task: {next_open}\n" + section[insert_at:]

    return body[:start] + section + body[end:]


def next_open_task_id(section: str) -> str:
    tasks = parse_plan_tasks(section)
    for task in tasks:
        if not task.done:
            return task.id
    return ""


def plan_progress_label(plan_status: str, current_task: str, section: Optional[str]) -> str:
    """Short Status.md suffix, e.g. `plan in-progress · T02/T03`."""
    label = f"plan {plan_status}"
    if not section:
        return label
    tasks = parse_plan_tasks(section)
    if not tasks:
        return label
    last = tasks[-1].id
    if current_task:
        return f"{label} · {current_task}/{last}"
    done = sum(1 for t in tasks if t.done)
    return f"{label} · {done}/{len(tasks)}"
