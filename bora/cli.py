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
from .lint import lint_all
from .paths import (
    AGENTS_FILE,
    ProjectPathError,
    VALID_PRIORITIES,
    VALID_STATUSES,
    VALID_TYPES,
    discover_project_file,
    find_repo_root,
    parse_project_path,
    parse_tags,
    project_dir,
    project_file,
    project_name,
    project_tickets_dir,
    require_repo_root,
    requirements_file,
    split_trailing_tags,
    status_file,
)
from .profile import read_profile, require_profile, write_profile
from .upgrade import agents_template_is_stale, apply_upgrade, inspect_upgrade
from .plan import (
    VALID_PLAN_STATUSES,
    extract_plan_section,
    next_open_task_id,
    parse_plan_tasks,
    set_current_task_line,
    set_plan_status_line,
    set_task_checkbox,
)
from .writer_chapter import create_chapter
from .writer_init import init_writer_project
from .writer_skill import install_obsidian, uninstall_obsidian
from .writer_status import compile_status as compile_write_status
from .skill import TOOLS, install as install_skill, list_status as skill_list_status, uninstall as uninstall_skill
from .status import write_status_md
from .templates import AGENTS_MD, REQUIREMENTS_MD_TEMPLATE, render_project_frontmatter, render_project_md
from .ticket import find_ticket, load_all_tickets, parse_ticket
from .routing import RoutingConfigError, resolve_effective_routing


# =============================================================================
# Helpers
# =============================================================================


def _open_in_editor(path: Path) -> None:
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    if not editor or not sys.stdin.isatty():
        return
    if not shutil.which(editor.split()[0]):
        return
    try:
        subprocess.run([*editor.split(), str(path)], check=False)
    except (OSError, subprocess.SubprocessError):
        pass


def _regenerate_status(root: Path, project_path: Optional[str] = None, *, quiet: bool = False) -> None:
    if not project_path:
        return
    path = write_status_md(root, project_path)
    if not quiet:
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        click.echo(f"Status.md updated → {rel}", err=True)


def _warn_stale_agents(root: Path) -> None:
    if agents_template_is_stale(root):
        click.echo(
            f"Note: AGENTS.md is not in sync with bora {__version__}. "
            "Run `bora dev upgrade`.",
            err=True,
        )


def _dev_project(project_path: str) -> tuple[Path, str]:
    root = require_repo_root()
    _warn_stale_agents(root)
    try:
        segments = parse_project_path(project_path)
    except ProjectPathError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    directory = project_dir(root, project_path)
    name = project_name(segments)
    if not directory.is_dir() or discover_project_file(directory, name) is None:
        click.echo(
            f"Error: missing project briefing for {project_path}; "
            f"expected '(YYYY-MM-DD) {name}.md'",
            err=True,
        )
        sys.exit(1)
    return root, project_path


def _print_lint_issues(issues, root: Path, header: Optional[str] = None) -> bool:
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


_TOOL_CHOICES = sorted(TOOLS.keys()) + ["all"]


def _resolve_tools(*names: str):
    seen: dict[str, object] = {}
    for raw in names:
        key = raw.lower()
        if key == "all":
            for t in TOOLS.values():
                seen.setdefault(t.key, t)
        else:
            seen.setdefault(key, TOOLS[key])
    return list(seen.values())


def _project_root_or_none(project: bool) -> Optional[Path]:
    if not project:
        return None
    return require_repo_root()


def _get_skip_flag(ctx: click.Context) -> bool:
    """Walk up the context chain to find skip_profile_check from the root."""
    obj = ctx.obj
    if isinstance(obj, dict):
        return obj.get("skip_profile_check", False)
    return False


def _parse_init_path_and_tags(project_path: str, tags_option: Optional[str]) -> tuple[str, Optional[list[str]]]:
    path, trailing = split_trailing_tags(project_path)
    if tags_option and trailing:
        click.echo("Error: pass tags via --tags or trailing [brackets], not both.", err=True)
        sys.exit(1)
    raw_tags = tags_option or trailing
    parsed = parse_tags(raw_tags) if raw_tags else None
    segments = parse_project_path(path)
    if parsed is not None and len(parsed) != len(segments):
        click.echo(
            f"Error: --tags has {len(parsed)} values but path has {len(segments)} segments.",
            err=True,
        )
        sys.exit(1)
    return path, parsed


# =============================================================================
# Root group — profile-aware help filtering
# =============================================================================


class _ProfileAwareGroup(click.Group):
    """Root Click group with profile-aware help filtering and expanded command listing."""

    def list_commands(self, ctx: click.Context):
        commands = super().list_commands(ctx)
        root = find_repo_root()
        if root is None:
            return commands
        data = read_profile(root)
        if data is None:
            return commands
        profile = data.get("profile")
        if profile == "dev":
            return [c for c in commands if c != "write"]
        if profile == "write":
            return [c for c in commands if c != "dev"]
        return commands

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        root = find_repo_root()
        profile = None
        if root:
            data = read_profile(root)
            if data:
                profile = data.get("profile")
        if profile != "write":
            self._format_profile_section(ctx, formatter, "dev", "Dev Profile Commands")
        if profile != "dev":
            self._format_profile_section(ctx, formatter, "write", "Write Profile Commands")

    def _format_profile_section(
        self,
        ctx: click.Context,
        formatter: click.HelpFormatter,
        group_name: str,
        section_title: str,
    ) -> None:
        group = self.commands.get(group_name)
        if group is None:
            return
        visible = [
            (name, group.commands[name])
            for name in group.list_commands(ctx)
            if name in group.commands and not group.commands[name].hidden
        ]
        if not visible:
            return
        col_width = max(len(f"{group_name} {name}") for name, _ in visible)
        limit = max(formatter.width - col_width - 6, 20)
        rows = [
            (f"{group_name} {name}", cmd.get_short_help_str(limit=limit))
            for name, cmd in visible
        ]
        with formatter.section(section_title):
            formatter.write_dl(rows)


@click.group(cls=_ProfileAwareGroup, context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, prog_name="bora")
@click.option(
    "--skip-profile-check",
    is_flag=True,
    default=False,
    hidden=True,
    help="Bypass profile locking (advanced users only).",
)
@click.pass_context
def main(ctx: click.Context, skip_profile_check: bool) -> None:
    """A structured collaboration framework for human-AI projects.

    Use 'bora dev' for software development projects (tickets, context,
    lint) or 'bora write' for creative writing projects (chapters, status).
    Run any command with -h for full details.
    """
    ctx.ensure_object(dict)
    ctx.obj["skip_profile_check"] = skip_profile_check


# =============================================================================
# dev group
# =============================================================================


@main.group()
@click.pass_context
def dev(ctx: click.Context) -> None:
    """Dev profile commands (tickets, status, lint, context, skills)."""
    if ctx.invoked_subcommand == "init":
        return
    root = find_repo_root()
    if root is not None:
        require_profile(root, "dev", skip_check=_get_skip_flag(ctx))


# =============================================================================
# dev init
# =============================================================================


@dev.command("init")
@click.argument("project_path")
@click.option("--tags", default=None, help="CSV labels matching path segments.")
@click.option("--force", is_flag=True, help="Overwrite existing scaffold files.")
def dev_init(project_path: str, tags: Optional[str], force: bool) -> None:
    """Scaffold a hierarchical dev project under docs/ai/<project_path>/.

    PROJECT_PATH is required (Codebase/Target/Project, depth >= 2).
    Creates a dated project briefing, a dated Requirements file,
    Status.md, and tickets/ inside that path. Writes root AGENTS.md
    only if it does not already exist (use --force to overwrite it).
    """
    try:
        path, parsed_tags = _parse_init_path_and_tags(project_path, tags)
    except ProjectPathError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    root = Path.cwd()
    briefing = project_file(root, path)
    reqs = requirements_file(root, path)
    status = status_file(root, path)
    tickets = project_tickets_dir(root, path)

    if not force:
        existing = [p for p in (briefing, reqs, status) if p.exists()]
        if existing:
            click.echo("Refusing to overwrite existing files:", err=True)
            for p in existing:
                click.echo(f"  {p.relative_to(root)}", err=True)
            click.echo("Use --force to overwrite.", err=True)
            sys.exit(1)

    write_profile(root, "dev")
    click.echo("Created .bora/profile.json")

    agents = root / AGENTS_FILE
    if not agents.exists() or force:
        agents.write_text(AGENTS_MD, encoding="utf-8")
        click.echo(f"Created {AGENTS_FILE}")

    tickets.mkdir(parents=True, exist_ok=True)
    gitkeep = tickets / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("", encoding="utf-8")

    segments = parse_project_path(path)
    name = project_name(segments)
    today = date.today().isoformat()
    hierarchy = list(segments)
    briefing.write_text(render_project_md(hierarchy, parsed_tags, today), encoding="utf-8")
    reqs_body = REQUIREMENTS_MD_TEMPLATE.split("---", 2)[-1].format(project_name=name)
    reqs.write_text(
        render_project_frontmatter(hierarchy, parsed_tags, today) + reqs_body,
        encoding="utf-8",
    )
    write_status_md(root, path)

    click.echo(f"Created {briefing.relative_to(root)}")
    click.echo(f"Created {reqs.relative_to(root)}")
    click.echo(f"Created {status.relative_to(root)}")
    click.echo(f"Created {tickets.relative_to(root)}")

    click.echo("\nDev project scaffolded. Next steps:")
    click.echo(f"  1. Edit {briefing.relative_to(root)}")
    click.echo("     (or point your AI agent at it) so it describes what you're building.")
    click.echo("  2. Discuss architecture with the agent. Approve the Requirements file")
    click.echo("     when it looks right. Do not create tickets yourself.")
    click.echo('  3. Tell the agent to go. It will:')
    click.echo("       - create tickets from the Requirements Tasks Breakdown")
    click.echo("       - ask once whether to use an isolated worktree")
    click.echo("       - for each ticket: plan, TDD, verify, then review")
    click.echo("       - show completed vs remaining after each ticket")
    click.echo("         (it will not ask \"should I continue?\")")
    click.echo("       - when the board is done, offer merge, PR, or keep")
    click.echo("\n  You run bora for setup (init, skill install, upgrade).")
    click.echo("  The agent runs ticket, plan, status, and lint commands.")
    click.echo("  If skills are not installed yet: bora dev skill install all")


# =============================================================================
# dev project
# =============================================================================


@dev.command("project", hidden=True)
@click.argument("args", nargs=-1)
def dev_project(args: tuple[str, ...]) -> None:
    """Removed in 0.4.5 — use bora dev init <path> --tags ..."""
    click.echo(
        "bora dev project is removed in 0.4.5 — use bora dev init <path> --tags ...",
        err=True,
    )
    sys.exit(1)


# =============================================================================
# dev ticket
# =============================================================================


@dev.group()
def ticket() -> None:
    """Create, update, list, and search tickets."""


@ticket.command("new")
@click.argument("project_path")
@click.argument("title")
@click.option(
    "--type", "ticket_type",
    type=click.Choice(sorted(VALID_TYPES)),
    default="feature", show_default=True,
)
@click.option("--priority", type=click.Choice(sorted(VALID_PRIORITIES)), default="medium", show_default=True)
@click.option("--parent", default="", help="Parent ticket id (for child tickets).")
@click.option("--no-edit", is_flag=True, help="Don't open the new ticket in $EDITOR.")
def ticket_new(project_path: str, title: str, ticket_type: str, priority: str, parent: str, no_edit: bool) -> None:
    """Create a new ticket in a project's tickets/ directory."""
    root, project_path = _dev_project(project_path)
    tdir = project_tickets_dir(root, project_path)
    if parent:
        parent_ticket = find_ticket(tdir, parent)
        if parent_ticket is None:
            click.echo(f"Error: parent ticket not found: {parent}", err=True)
            sys.exit(1)
        parent = parent_ticket.id
    path = create_ticket(tdir, title=title, ticket_type=ticket_type, priority=priority, parent=parent)
    click.echo(f"Created {path.relative_to(root)}")
    if not no_edit:
        _open_in_editor(path)
    _regenerate_status(root, project_path)


@ticket.command("list")
@click.argument("project_path")
@click.option("--status", type=click.Choice(sorted(VALID_STATUSES)), help="Filter by status.")
@click.option("--type", "ticket_type", type=click.Choice(sorted(VALID_TYPES)), help="Filter by type.")
@click.option("--priority", type=click.Choice(sorted(VALID_PRIORITIES)), help="Filter by priority.")
@click.option("--blocked", is_flag=True, help="Show only tickets with unfinished dependencies.")
def ticket_list(project_path: str, status: Optional[str], ticket_type: Optional[str], priority: Optional[str], blocked: bool) -> None:
    """List tickets in a table."""
    root, project_path = _dev_project(project_path)
    tickets = load_all_tickets(project_tickets_dir(root, project_path))

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

    rows = [(t.id, t.status, t.priority, t.type, t.title) for t in tickets]
    headers = ("ID", "STATUS", "PRIORITY", "TYPE", "TITLE")
    widths = [max(len(headers[i]), max(len(row[i]) for row in rows)) for i in range(len(headers))]
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
@click.argument("project_path")
@click.argument("ticket_id")
def ticket_show(project_path: str, ticket_id: str) -> None:
    """Print a ticket's full contents (fuzzy id match)."""
    root, project_path = _dev_project(project_path)
    t = find_ticket(project_tickets_dir(root, project_path), ticket_id)
    if t is None:
        click.echo(f"No ticket matched: {ticket_id}", err=True)
        sys.exit(1)
    click.echo(t.path.read_text(encoding="utf-8"))


@ticket.command("set")
@click.argument("project_path")
@click.argument("ticket_id")
@click.argument("field")
@click.argument("value")
def ticket_set(project_path: str, ticket_id: str, field: str, value: str) -> None:
    """Update a frontmatter field on a ticket."""
    root, project_path = _dev_project(project_path)
    tdir = project_tickets_dir(root, project_path)
    t = find_ticket(tdir, ticket_id)
    if t is None:
        click.echo(f"No ticket matched: {ticket_id}", err=True)
        sys.exit(1)

    settable = {"title", "type", "priority", "status", "notes", "parent"}
    if field not in settable:
        click.echo(f"Error: cannot set field {field!r}. Settable fields: {sorted(settable)}", err=True)
        sys.exit(1)

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
        parent = find_ticket(tdir, value)
        if parent is None:
            click.echo(f"Error: parent ticket not found: {value}", err=True)
            sys.exit(1)
        value = parent.id

    t.set_field(field, value)
    if field == "status":
        if value == "done" and not t.frontmatter.get("closed"):
            t.frontmatter["closed"] = date.today()
        elif value != "done" and t.frontmatter.get("closed"):
            t.frontmatter["closed"] = None
    t.save()
    click.echo(f"Updated {t.id}: {field} = {value}")
    _regenerate_status(root, project_path)


@ticket.command("note")
@click.argument("project_path")
@click.argument("ticket_id")
@click.argument("text")
def ticket_note(project_path: str, ticket_id: str, text: str) -> None:
    """Append a dated entry to a ticket's body Notes section."""
    root, project_path = _dev_project(project_path)
    t = find_ticket(project_tickets_dir(root, project_path), ticket_id)
    if t is None:
        click.echo(f"No ticket matched: {ticket_id}", err=True)
        sys.exit(1)
    t.append_note(text)
    t.save()
    click.echo(f"Appended note to {t.id}")
    _regenerate_status(root, project_path)


@ticket.command("subtask")
@click.argument("project_path")
@click.argument("ticket_id")
@click.argument("subtask_id")
@click.argument("status")
def ticket_subtask(project_path: str, ticket_id: str, subtask_id: str, status: str) -> None:
    """Update a frontmatter subtask's status."""
    from .paths import VALID_SUBTASK_STATUSES
    root, project_path = _dev_project(project_path)
    t = find_ticket(project_tickets_dir(root, project_path), ticket_id)
    if t is None:
        click.echo(f"No ticket matched: {ticket_id}", err=True)
        sys.exit(1)
    if status not in VALID_SUBTASK_STATUSES:
        click.echo(
            f"Error: invalid subtask status {status!r}. Expected one of {sorted(VALID_SUBTASK_STATUSES)}",
            err=True,
        )
        sys.exit(1)
    if not t.set_subtask_status(subtask_id, status):
        click.echo(f"Error: subtask {subtask_id!r} not found in {t.id}", err=True)
        sys.exit(1)
    t.save()
    click.echo(f"Updated {t.id}: subtask {subtask_id} = {status}")
    _regenerate_status(root, project_path)


# =============================================================================
# dev status
# =============================================================================


@dev.command("status")
@click.argument("project_path")
def dev_status(project_path: str) -> None:
    """Regenerate Status.md from current ticket state for PROJECT_PATH."""
    root, project_path = _dev_project(project_path)
    path = write_status_md(root, project_path)
    click.echo(f"Wrote {path.relative_to(root)}")


# =============================================================================
# dev context
# =============================================================================


@dev.command("context")
@click.argument("project_path")
@click.option("--budget", type=int, default=None, help="Maximum approximate token count.")
def dev_context(project_path: str, budget: Optional[int]) -> None:
    """Print briefing content for a fresh model session.

    Pipe to your clipboard or paste into a chat to brief a model:
        bora dev context <project_path> | pbcopy
        bora dev context <project_path> --budget 8000
    """
    root, project_path = _dev_project(project_path)
    content = assemble_context(root, project_path, budget=budget)
    click.echo(content, nl=False)
    if budget is not None:
        click.echo(f"\n[~{estimate_tokens(content)} tokens, budget {budget}]", err=True)


# =============================================================================
# dev lint
# =============================================================================


@dev.command("lint")
@click.argument("project_path")
def dev_lint(project_path: str) -> None:
    """Validate frontmatter and cross-references across a project's tickets."""
    root, project_path = _dev_project(project_path)
    issues = lint_all(project_tickets_dir(root, project_path))
    if not issues:
        click.echo("OK — no issues found.")
        return
    has_errors = _print_lint_issues(issues, root, header=f"Found {len(issues)} issue(s):")
    if has_errors:
        sys.exit(1)


# =============================================================================
# dev plan
# =============================================================================


@dev.group()
def plan() -> None:
    """Show or update a ticket's ## Implementation plan section."""


def _load_ticket_or_exit(root: Path, project_path: str, ticket_id: str):
    t = find_ticket(project_tickets_dir(root, project_path), ticket_id)
    if t is None:
        click.echo(f"No ticket matched: {ticket_id}", err=True)
        sys.exit(1)
    return t


@plan.command("show")
@click.argument("project_path")
@click.argument("ticket_id")
def plan_show(project_path: str, ticket_id: str) -> None:
    """Print a ticket's ## Implementation plan section."""
    root, project_path = _dev_project(project_path)
    t = _load_ticket_or_exit(root, project_path, ticket_id)
    section = extract_plan_section(t.body)
    if section is None:
        click.echo(
            f"Error: {t.id} has no ## Implementation plan section. "
            "Add one to the ticket (see the ticket template).",
            err=True,
        )
        sys.exit(1)
    click.echo(section, nl=False)
    if not section.endswith("\n"):
        click.echo()


@plan.command("set")
@click.argument("project_path")
@click.argument("ticket_id")
@click.argument("field")
@click.argument("value")
def plan_set(project_path: str, ticket_id: str, field: str, value: str) -> None:
    """Set plan_status (field=status) or current_task on a ticket."""
    root, project_path = _dev_project(project_path)
    t = _load_ticket_or_exit(root, project_path, ticket_id)
    if field not in {"status", "current_task"}:
        click.echo(
            f"Error: cannot set field {field!r}. Settable fields: current_task, status",
            err=True,
        )
        sys.exit(1)
    if field == "status":
        if value not in VALID_PLAN_STATUSES:
            click.echo(
                f"Error: invalid plan status {value!r}. "
                f"Expected one of {sorted(VALID_PLAN_STATUSES)}",
                err=True,
            )
            sys.exit(1)
        t.set_field("plan_status", value)
        t.body = set_plan_status_line(t.body, value)
        if value == "in-progress" and t.status == "todo":
            t.set_field("status", "in-progress")
        elif value == "blocked":
            t.set_field("status", "blocked")
        click.echo(f"Updated {t.id}: plan_status = {value}")
    else:
        t.set_field("current_task", value)
        t.body = set_current_task_line(t.body, value)
        click.echo(f"Updated {t.id}: current_task = {value}")
    t.save()
    _regenerate_status(root, project_path)


@plan.command("task")
@click.argument("project_path")
@click.argument("ticket_id")
@click.argument("task_id")
@click.argument("status")
def plan_task(project_path: str, ticket_id: str, task_id: str, status: str) -> None:
    """Mark a plan task todo or done."""
    root, project_path = _dev_project(project_path)
    t = _load_ticket_or_exit(root, project_path, ticket_id)
    if status not in {"todo", "done"}:
        click.echo("Error: task status must be todo or done", err=True)
        sys.exit(1)
    try:
        t.body = set_task_checkbox(t.body, task_id, done=(status == "done"))
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    section = extract_plan_section(t.body)
    nxt = next_open_task_id(section or "")
    t.set_field("current_task", nxt or None)
    if section and parse_plan_tasks(section):
        if nxt:
            t.set_field("plan_status", "in-progress")
            t.body = set_plan_status_line(t.body, "in-progress")
            if t.status == "todo":
                t.set_field("status", "in-progress")
        else:
            t.set_field("plan_status", "done")
            t.body = set_plan_status_line(t.body, "done")
    t.save()
    click.echo(f"Updated {t.id}: {task_id} = {status}")
    _regenerate_status(root, project_path)


# =============================================================================
# dev upgrade
# =============================================================================


@dev.command("upgrade")
@click.option("--dry-run", is_flag=True, help="Show what would change without writing.")
@click.option("--agents-only", is_flag=True, help="Only refresh AGENTS.md.")
@click.option("--skills-only", is_flag=True, help="Only refresh already-installed skills.")
@click.option("--force", is_flag=True, help="Overwrite a dirty unmarked AGENTS.md.")
def dev_upgrade(dry_run: bool, agents_only: bool, skills_only: bool, force: bool) -> None:
    """Refresh AGENTS.md and the skill pack to match this CLI version."""
    root = find_repo_root()
    if root is None:
        click.echo(
            "Error: not inside a bora project. Run `bora dev init` first.",
            err=True,
        )
        sys.exit(1)
    profile = read_profile(root)
    agents = root / AGENTS_FILE
    if not agents.exists() and (profile or {}).get("profile") != "dev":
        click.echo(
            "Error: no AGENTS.md and no dev profile. Run `bora dev init <project_path>` first.",
            err=True,
        )
        sys.exit(1)
    if dry_run:
        plan = inspect_upgrade(root)
        click.echo(f"AGENTS.md: {plan.agents_action} (version={plan.agents_version!r})")
        if plan.dirty_unmarked:
            click.echo("AGENTS.md has uncommitted changes (would refuse without --force).")
        if plan.skill_paths:
            click.echo("Skills that would be rewritten:")
            for p in plan.skill_paths:
                click.echo(f"  {p}")
        else:
            click.echo("No installed skills found. Hint: bora dev skill install <tool>")
        return
    try:
        apply_upgrade(
            root,
            dry_run=False,
            agents_only=agents_only,
            skills_only=skills_only,
            force=force,
        )
    except PermissionError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    click.echo(f"Updated AGENTS.md to bora {__version__}.")
    click.echo("Review `git diff AGENTS.md` and keep local rules under Project-specific instructions.")
    plan = inspect_upgrade(root)
    if not plan.skill_paths and not skills_only:
        click.echo("Hint: no skills installed. Run `bora dev skill install <tool>` (or all).")
    elif not agents_only:
        click.echo("Refreshed installed skill pack.")


# =============================================================================
# dev decision
# =============================================================================


@dev.command("decision", hidden=True)
@click.argument("args", nargs=-1)
def dev_decision(args: tuple[str, ...]) -> None:
    """Removed in 0.4.5 — record decisions in the project's Requirements file."""
    click.echo(
        "bora dev decision is removed in 0.4.5 — record decisions in the project's Requirements file",
        err=True,
    )
    sys.exit(1)


# =============================================================================
# dev skill
# =============================================================================


@dev.group()
def skill() -> None:
    """Install or remove the bora skill pack for AI coding tools."""


@skill.command("install")
@click.argument("tool", type=click.Choice(_TOOL_CHOICES, case_sensitive=False))
@click.option("--project", is_flag=True, help="Install into the current repo instead of user level.")
@click.option("--force", is_flag=True, help="Overwrite an existing SKILL.md even if it isn't ours.")
def skill_install(tool: str, project: bool, force: bool) -> None:
    """Install the bora skill pack for an AI tool (claude, opencode, all)."""
    root = _project_root_or_none(project)
    had_error = False
    for t in _resolve_tools(tool):
        try:
            result = install_skill(t, project_root=root, force=force)
        except FileExistsError as exc:
            click.echo(f"{t.display}: {exc}", err=True)
            had_error = True
            continue
        verb = "Updated" if result.overwritten else "Installed"
        click.echo(f"{verb} bora skill for {t.display} → {result.path}")
    if had_error:
        sys.exit(1)


@skill.command("uninstall")
@click.argument("tool", type=click.Choice(_TOOL_CHOICES, case_sensitive=False))
@click.option("--project", is_flag=True, help="Uninstall from the current repo instead of user level.")
@click.option("--force", is_flag=True, help="Remove the skill directory even if its SKILL.md isn't ours.")
def skill_uninstall(tool: str, project: bool, force: bool) -> None:
    """Uninstall the bora skill for an AI tool (claude, opencode, all)."""
    root = _project_root_or_none(project)
    for t in _resolve_tools(tool):
        result = uninstall_skill(t, project_root=root, force=force)
        if result.removed:
            click.echo(f"Removed bora skill for {t.display} ({result.path})")
        else:
            click.echo(f"{t.display}: {result.reason} ({result.path})", err=True)


@skill.command("list")
def skill_list() -> None:
    """Show where the bora skill is installed for each known tool."""
    root = find_repo_root()
    rows = skill_list_status(project_root=root)
    width_tool = max(len(s.tool.display) for s in rows)
    width_scope = max(len(s.scope) for s in rows)
    for s in rows:
        if not s.installed:
            mark = "not installed"
        elif s.is_ours:
            mark = "installed"
        else:
            mark = "installed (foreign SKILL.md)"
        click.echo(f"{s.tool.display:<{width_tool}}  {s.scope:<{width_scope}}  {mark:<28}  {s.path}")


# =============================================================================
# dev routing
# =============================================================================

_ROUTING_TIER_ORDER = ("premium", "standard", "economy", "local")


@dev.group()
def routing() -> None:
    """Inspect model-tier routing (informational only)."""


@routing.command("show")
@click.argument("project_path")
def routing_show(project_path: str) -> None:
    """Print effective routing for a project.

    Informational only: does not contact a router or write models.yaml.
    """
    root, _ = _dev_project(project_path)
    try:
        resolved = resolve_effective_routing(root)
    except RoutingConfigError as exc:
        click.echo(f"Configuration error: {exc}", err=True)
        sys.exit(1)

    status = "enabled" if resolved.enabled else "disabled"
    click.echo("Bora model routing")
    click.echo()
    click.echo(f"Status: {status}")
    click.echo()
    click.echo(f"{'Tier':<9}  Route")
    click.echo(f"{'-' * 9}  {'-' * 16}")
    for tier in _ROUTING_TIER_ORDER:
        if resolved.enabled:
            route = resolved.tiers.get(tier) or "(unset)"
        else:
            route = "(unset)"
        click.echo(f"{tier:<9}  {route}")


# =============================================================================
# write group
# =============================================================================


@main.group()
@click.pass_context
def write(ctx: click.Context) -> None:
    """Write profile commands (chapters, research, status, skills)."""
    if ctx.invoked_subcommand == "init":
        return
    root = find_repo_root()
    if root is not None:
        require_profile(root, "write", skip_check=_get_skip_flag(ctx))


# =============================================================================
# write init
# =============================================================================


@write.command("init")
@click.option("--force", is_flag=True, help="Overwrite existing files. Use with caution.")
def write_init(force: bool) -> None:
    """Scaffold a new write project — AGENTS.md, Summary.md, chapters/."""
    init_writer_project(Path.cwd(), force=force)


# =============================================================================
# write chapter
# =============================================================================


@write.command("chapter")
@click.argument("name")
def write_chapter(name: str) -> None:
    """Create a numbered chapter directory with manuscript and research files."""
    root = find_repo_root()
    if root is None:
        click.echo("Error: not inside a bora write project. Run `bora write init` first.", err=True)
        sys.exit(1)
    create_chapter(root, name)


# =============================================================================
# write status
# =============================================================================


@write.command("status")
def write_status() -> None:
    """Compile project context and print a structured briefing for your AI model.

    Archives any existing Summary.md to Summary/ before printing. Safe to rerun.
    Pipe or paste the output to your AI model, then save its response as Summary.md.
    """
    root = find_repo_root()
    if root is None:
        click.echo("Error: not inside a bora write project. Run `bora write init` first.", err=True)
        sys.exit(1)
    click.echo(compile_write_status(root))


# =============================================================================
# write skill
# =============================================================================


@write.group(name="skill")
def write_skill() -> None:
    """Install or remove write-profile skills."""


@write_skill.command("install")
@click.argument("tool", type=click.Choice(["obsidian"], case_sensitive=False))
@click.option("--force", is_flag=True, help="Overwrite existing installation.")
def write_skill_install(tool: str, force: bool) -> None:
    """Install a write-profile skill (obsidian)."""
    root = find_repo_root()
    if root is None:
        click.echo("Error: not inside a bora write project. Run `bora write init` first.", err=True)
        sys.exit(1)
    if tool == "obsidian":
        try:
            result = install_obsidian(root, force=force)
        except FileExistsError as exc:
            click.echo(str(exc), err=True)
            sys.exit(1)
        verb = "Updated" if result.overwritten else "Installed"
        click.echo(f"{verb} Obsidian skill → {result.path.relative_to(root)}")


@write_skill.command("uninstall")
@click.argument("tool", type=click.Choice(["obsidian"], case_sensitive=False))
@click.option("--force", is_flag=True, help="Remove even if SKILL.md is missing.")
def write_skill_uninstall(tool: str, force: bool) -> None:
    """Uninstall a write-profile skill (obsidian)."""
    root = find_repo_root()
    if root is None:
        click.echo("Error: not inside a bora write project.", err=True)
        sys.exit(1)
    if tool == "obsidian":
        result = uninstall_obsidian(root, force=force)
        if result.removed:
            click.echo(f"Removed Obsidian skill ({result.path.relative_to(root)})")
        else:
            click.echo(f"obsidian: {result.reason} ({result.path})", err=True)


# =============================================================================
# Deprecated top-level bora init (migration stub)
# =============================================================================


@main.command("init", hidden=True)
def deprecated_init() -> None:
    """Deprecated. Use 'bora dev init' or 'bora write init'."""
    click.echo(
        "⚠️  bora init is deprecated in 0.3.0.\n"
        "Use 'bora dev init' for a developer project\n"
        " or 'bora write init' for a writer project."
    )


if __name__ == "__main__":
    main()
