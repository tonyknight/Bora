"""CLI entry point and subcommands."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Optional

import click

from . import __version__
from .context import assemble_context, estimate_tokens
from .create import create_ticket
from .lint import lint_all, lint_ticket
from .paths import (
    AGENTS_FILE,
    ARCHITECTURE_FILE,
    DOCS_DIR,
    PROJECT_FILE,
    TICKETS_DIR,
    VALID_PRIORITIES,
    VALID_STATUSES,
    VALID_TYPES,
    docs_dir,
    find_repo_root,
    require_repo_root,
    tickets_dir,
)
from .status import write_tasks_md
from .templates import AGENTS_MD, ARCHITECTURE_MD_TEMPLATE, PROJECT_MD_TEMPLATE
from .ticket import find_ticket, load_all_tickets, parse_ticket


# =============================================================================
# Helpers
# =============================================================================


def _open_in_editor(path: Path) -> None:
    """Open a file in the user's $EDITOR. Silently does nothing if not set
    or in a non-interactive context. Models running this in a non-interactive
    shell will get the file path printed and can read it themselves."""
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    if not editor or not sys.stdin.isatty():
        return
    if not shutil.which(editor.split()[0]):
        return
    try:
        subprocess.run([*editor.split(), str(path)], check=False)
    except (OSError, subprocess.SubprocessError):
        pass


def _regenerate_status(root: Path, *, quiet: bool = False) -> None:
    """Regenerate Tasks.md and optionally print a notice."""
    path = write_tasks_md(root)
    if not quiet:
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        click.echo(f"Tasks.md updated → {rel}", err=True)


def _print_lint_issues(issues, root: Path, header: Optional[str] = None) -> bool:
    """Print issues. Returns True if any errors (not just warnings)."""
    if not issues:
        return False
    if header:
        click.echo(header, err=True)
    has_errors = False
    for issue in issues:
        click.echo(issue.format(root), err=True)
        if issue.severity == "error":
            has_errors = True
    return has_errors


# =============================================================================
# Top-level CLI
# =============================================================================


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, prog_name="bora")
def main():
    """A structured collaboration framework for human-AI coding projects."""


# =============================================================================
# init
# =============================================================================


@main.command()
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing files. Use with caution.",
)
def init(force: bool) -> None:
    """Scaffold AGENTS.md and docs/ai/ in the current directory."""
    root = Path.cwd()
    today = date.today().isoformat()

    files_to_create = [
        (root / AGENTS_FILE, AGENTS_MD),
        (root / PROJECT_FILE, PROJECT_MD_TEMPLATE.format(today=today)),
        (root / ARCHITECTURE_FILE, ARCHITECTURE_MD_TEMPLATE.format(today=today)),
    ]

    # Refuse to overwrite unless --force
    if not force:
        existing = [p for p, _ in files_to_create if p.exists()]
        if existing:
            click.echo("Refusing to overwrite existing files:", err=True)
            for p in existing:
                click.echo(f"  {p.relative_to(root)}", err=True)
            click.echo("Use --force to overwrite.", err=True)
            sys.exit(1)

    # Create directories
    (root / TICKETS_DIR).mkdir(parents=True, exist_ok=True)

    # Write files
    for path, content in files_to_create:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        click.echo(f"Created {path.relative_to(root)}")

    # Generate initial Tasks.md
    write_tasks_md(root)
    click.echo(f"Created {DOCS_DIR}/Tasks.md")

    click.echo("\nProject scaffolded. Next steps:")
    click.echo("  1. Edit docs/ai/Project.md to describe what you're building.")
    click.echo("  2. Edit docs/ai/Architecture.md once design takes shape.")
    click.echo("  3. Create your first ticket: bora ticket new \"<title>\"")


# =============================================================================
# ticket
# =============================================================================


@main.group()
def ticket() -> None:
    """Manage tickets."""


@ticket.command("new")
@click.argument("title")
@click.option(
    "--type",
    "ticket_type",
    type=click.Choice(sorted(VALID_TYPES)),
    default="feature",
    show_default=True,
)
@click.option(
    "--priority",
    type=click.Choice(sorted(VALID_PRIORITIES)),
    default="medium",
    show_default=True,
)
@click.option(
    "--parent",
    default="",
    help="Parent ticket id (for child tickets).",
)
@click.option(
    "--no-edit",
    is_flag=True,
    help="Don't open the new ticket in $EDITOR.",
)
def ticket_new(title: str, ticket_type: str, priority: str, parent: str, no_edit: bool) -> None:
    """Create a new ticket."""
    root = require_repo_root()

    # If parent specified, validate it exists
    if parent:
        parent_ticket = find_ticket(tickets_dir(root), parent)
        if parent_ticket is None:
            click.echo(f"Error: parent ticket not found: {parent}", err=True)
            sys.exit(1)
        # Use the resolved id, not whatever shorthand was passed
        parent = parent_ticket.id

    path = create_ticket(
        tickets_dir(root),
        title=title,
        ticket_type=ticket_type,
        priority=priority,
        parent=parent,
    )
    rel = path.relative_to(root)
    click.echo(f"Created {rel}")

    if not no_edit:
        _open_in_editor(path)

    _regenerate_status(root)


@ticket.command("list")
@click.option(
    "--status",
    type=click.Choice(sorted(VALID_STATUSES)),
    help="Filter by status.",
)
@click.option(
    "--type",
    "ticket_type",
    type=click.Choice(sorted(VALID_TYPES)),
    help="Filter by type.",
)
@click.option(
    "--priority",
    type=click.Choice(sorted(VALID_PRIORITIES)),
    help="Filter by priority.",
)
@click.option(
    "--blocked",
    is_flag=True,
    help="Show only tickets with unfinished dependencies.",
)
def ticket_list(status: Optional[str], ticket_type: Optional[str], priority: Optional[str], blocked: bool) -> None:
    """List tickets in a table."""
    root = require_repo_root()
    tickets = load_all_tickets(tickets_dir(root))

    if status:
        tickets = [t for t in tickets if t.status == status]
    if ticket_type:
        tickets = [t for t in tickets if t.type == ticket_type]
    if priority:
        tickets = [t for t in tickets if t.priority == priority]
    if blocked:
        from .lint import get_blocked_tickets
        blocked_ids = set(get_blocked_tickets(tickets).keys())
        tickets = [t for t in tickets if t.id in blocked_ids]

    if not tickets:
        click.echo("No tickets match.")
        return

    # Render as a simple aligned table
    rows = [
        (t.id, t.status, t.priority, t.type, t.title)
        for t in tickets
    ]
    headers = ("ID", "STATUS", "PRIORITY", "TYPE", "TITLE")
    widths = [
        max(len(headers[i]), max(len(row[i]) for row in rows))
        for i in range(len(headers))
    ]
    # Cap title width so very long titles don't wreck the layout
    widths[-1] = min(widths[-1], 60)

    def fmt(row):
        return "  ".join(
            (cell if i == len(row) - 1 else cell.ljust(widths[i]))
            if len(cell) <= widths[i]
            else cell[:widths[i] - 1] + "…"
            for i, cell in enumerate(row)
        )

    click.echo(fmt(headers))
    click.echo("  ".join("-" * w for w in widths))
    for row in rows:
        click.echo(fmt(row))


@ticket.command("show")
@click.argument("ticket_id")
def ticket_show(ticket_id: str) -> None:
    """Print a ticket's full contents (fuzzy id match)."""
    root = require_repo_root()
    t = find_ticket(tickets_dir(root), ticket_id)
    if t is None:
        click.echo(f"No ticket matched: {ticket_id}", err=True)
        sys.exit(1)
    click.echo(t.path.read_text(encoding="utf-8"))


@ticket.command("set")
@click.argument("ticket_id")
@click.argument("field")
@click.argument("value")
def ticket_set(ticket_id: str, field: str, value: str) -> None:
    """Update a frontmatter field on a ticket.

    Validates field name and value. Setting status=done auto-populates the
    closed date. Setting status to anything else clears the closed date.
    """
    root = require_repo_root()
    t = find_ticket(tickets_dir(root), ticket_id)
    if t is None:
        click.echo(f"No ticket matched: {ticket_id}", err=True)
        sys.exit(1)

    # Validate field name — we allow the "settable" subset to keep this
    # command from being a foot-gun. Use direct file edits for unusual cases.
    settable = {"title", "type", "priority", "status", "notes", "parent"}
    if field not in settable:
        click.echo(
            f"Error: cannot set field {field!r}. Settable fields: {sorted(settable)}",
            err=True,
        )
        sys.exit(1)

    # Validate enumerated values
    if field == "type" and value not in VALID_TYPES:
        click.echo(f"Error: invalid type {value!r}. Expected one of {sorted(VALID_TYPES)}", err=True)
        sys.exit(1)
    if field == "priority" and value not in VALID_PRIORITIES:
        click.echo(f"Error: invalid priority {value!r}. Expected one of {sorted(VALID_PRIORITIES)}", err=True)
        sys.exit(1)
    if field == "status" and value not in VALID_STATUSES:
        click.echo(f"Error: invalid status {value!r}. Expected one of {sorted(VALID_STATUSES)}", err=True)
        sys.exit(1)

    if field == "parent" and value:
        parent = find_ticket(tickets_dir(root), value)
        if parent is None:
            click.echo(f"Error: parent ticket not found: {value}", err=True)
            sys.exit(1)
        value = parent.id

    t.set_field(field, value)

    # Status transitions: keep closed date in sync
    if field == "status":
        if value == "done" and not t.frontmatter.get("closed"):
            t.frontmatter["closed"] = date.today()
        elif value != "done" and t.frontmatter.get("closed"):
            t.frontmatter["closed"] = None

    t.save()
    click.echo(f"Updated {t.id}: {field} = {value}")
    _regenerate_status(root)


@ticket.command("note")
@click.argument("ticket_id")
@click.argument("text")
def ticket_note(ticket_id: str, text: str) -> None:
    """Append a dated entry to a ticket's body Notes section.

    Useful for the model (or human) to record progress without rewriting
    the whole file. Each entry gets today's date as a subheading.
    """
    root = require_repo_root()
    t = find_ticket(tickets_dir(root), ticket_id)
    if t is None:
        click.echo(f"No ticket matched: {ticket_id}", err=True)
        sys.exit(1)
    t.append_note(text)
    t.save()
    click.echo(f"Appended note to {t.id}")
    _regenerate_status(root)


@ticket.command("subtask")
@click.argument("ticket_id")
@click.argument("subtask_id")
@click.argument("status")
def ticket_subtask(ticket_id: str, subtask_id: str, status: str) -> None:
    """Update a frontmatter subtask's status."""
    from .paths import VALID_SUBTASK_STATUSES

    root = require_repo_root()
    t = find_ticket(tickets_dir(root), ticket_id)
    if t is None:
        click.echo(f"No ticket matched: {ticket_id}", err=True)
        sys.exit(1)

    if status not in VALID_SUBTASK_STATUSES:
        click.echo(
            f"Error: invalid subtask status {status!r}. "
            f"Expected one of {sorted(VALID_SUBTASK_STATUSES)}",
            err=True,
        )
        sys.exit(1)

    if not t.set_subtask_status(subtask_id, status):
        click.echo(f"Error: subtask {subtask_id!r} not found in {t.id}", err=True)
        sys.exit(1)

    t.save()
    click.echo(f"Updated {t.id}: subtask {subtask_id} = {status}")
    _regenerate_status(root)


# =============================================================================
# status
# =============================================================================


@main.command("status")
def cmd_status() -> None:
    """Regenerate Tasks.md from current ticket state."""
    root = require_repo_root()
    path = write_tasks_md(root)
    rel = path.relative_to(root)
    click.echo(f"Wrote {rel}")


# =============================================================================
# context
# =============================================================================


@main.command("context")
@click.option(
    "--budget",
    type=int,
    default=None,
    help="Maximum approximate token count. Truncates by dropping less-essential files.",
)
def cmd_context(budget: Optional[int]) -> None:
    """Print briefing content for a fresh model session.

    Pipe to your clipboard or paste into a chat to brief a model:
        bora context | pbcopy
        bora context --budget 8000
    """
    root = require_repo_root()
    content = assemble_context(root, budget=budget)
    click.echo(content, nl=False)
    if budget is not None:
        click.echo(
            f"\n[~{estimate_tokens(content)} tokens, budget {budget}]",
            err=True,
        )


# =============================================================================
# lint
# =============================================================================


@main.command("lint")
def cmd_lint() -> None:
    """Validate frontmatter and cross-references across all tickets."""
    root = require_repo_root()
    issues = lint_all(tickets_dir(root))

    if not issues:
        click.echo("OK — no issues found.")
        return

    has_errors = _print_lint_issues(issues, root, header=f"Found {len(issues)} issue(s):")
    if has_errors:
        sys.exit(1)


# =============================================================================
# decision
# =============================================================================


@main.group()
def decision() -> None:
    """Manage architecture decisions."""


@decision.command("new")
@click.argument("title")
def decision_new(title: str) -> None:
    """Append a new decision entry to Architecture.md and open it."""
    root = require_repo_root()
    arch_path = root / ARCHITECTURE_FILE
    if not arch_path.exists():
        click.echo(
            f"Error: {ARCHITECTURE_FILE} does not exist. Run `bora init` first.",
            err=True,
        )
        sys.exit(1)

    today = date.today().isoformat()
    entry = (
        f"\n### {today} — {title}\n\n"
        "**What was decided:** \n\n"
        "**Alternatives considered:** \n\n"
        "**Reasoning:** \n"
    )

    existing = arch_path.read_text(encoding="utf-8")
    # Append to end. We trust the user to have a "Decision log" heading;
    # if not, the entry just appears at the bottom.
    if not existing.endswith("\n"):
        existing += "\n"
    arch_path.write_text(existing + entry, encoding="utf-8")
    click.echo(f"Appended decision entry to {ARCHITECTURE_FILE}")
    _open_in_editor(arch_path)


if __name__ == "__main__":
    main()
