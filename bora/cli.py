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
from .profile import read_profile, require_profile, write_profile
from .writer_chapter import create_chapter
from .writer_init import init_writer_project
from .writer_skill import install_obsidian, uninstall_obsidian
from .writer_status import compile_status as compile_write_status
from .skill import TOOLS, install as install_skill, list_status as skill_list_status, uninstall as uninstall_skill
from .status import write_tasks_md
from .templates import AGENTS_MD, ARCHITECTURE_MD_TEMPLATE, PROJECT_MD_TEMPLATE
from .ticket import find_ticket, load_all_tickets, parse_ticket


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


def _regenerate_status(root: Path, *, quiet: bool = False) -> None:
    path = write_tasks_md(root)
    if not quiet:
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        click.echo(f"Tasks.md updated → {rel}", err=True)


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


# =============================================================================
# Root group — profile-aware help filtering
# =============================================================================


class _ProfileAwareGroup(click.Group):
    """Root Click group that hides the irrelevant profile subgroup from help."""

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
    """A structured collaboration framework for human-AI projects."""
    ctx.ensure_object(dict)
    ctx.obj["skip_profile_check"] = skip_profile_check


# =============================================================================
# dev group
# =============================================================================


@main.group()
@click.pass_context
def dev(ctx: click.Context) -> None:
    """Dev profile commands (tickets, status, lint, context, decisions, skills)."""
    if ctx.invoked_subcommand == "init":
        return
    root = find_repo_root()
    if root is not None:
        require_profile(root, "dev", skip_check=_get_skip_flag(ctx))


# =============================================================================
# dev init
# =============================================================================


@dev.command("init")
@click.argument(
    "tools",
    nargs=-1,
    type=click.Choice(_TOOL_CHOICES, case_sensitive=False),
)
@click.option("--force", is_flag=True, help="Overwrite existing files. Use with caution.")
@click.option(
    "--skill-global",
    is_flag=True,
    help="Install skills at the user level (~/.claude/) instead of inside this repo.",
)
def dev_init(tools: tuple, force: bool, skill_global: bool) -> None:
    """Scaffold a dev profile project (AGENTS.md, docs/ai/, tickets).

    Optionally install the bora skill for one or more AI tools in the same
    step: bora dev init claude, bora dev init all.
    """
    root = Path.cwd()
    today = date.today().isoformat()

    files_to_create = [
        (root / AGENTS_FILE, AGENTS_MD),
        (root / PROJECT_FILE, PROJECT_MD_TEMPLATE.format(today=today)),
        (root / ARCHITECTURE_FILE, ARCHITECTURE_MD_TEMPLATE.format(today=today)),
    ]

    if not force:
        existing = [p for p, _ in files_to_create if p.exists()]
        if (root / ".bora" / "profile.json").exists():
            existing.append(root / ".bora" / "profile.json")
        if existing:
            click.echo("Refusing to overwrite existing files:", err=True)
            for p in existing:
                click.echo(f"  {p.relative_to(root)}", err=True)
            click.echo("Use --force to overwrite.", err=True)
            sys.exit(1)

    (root / TICKETS_DIR).mkdir(parents=True, exist_ok=True)

    write_profile(root, "dev")
    click.echo("Created .bora/profile.json")

    for path, content in files_to_create:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        click.echo(f"Created {path.relative_to(root)}")

    write_tasks_md(root)
    click.echo(f"Created {DOCS_DIR}/Tasks.md")

    skill_errors = False
    if tools:
        skill_root = None if skill_global else root
        for t in _resolve_tools(*tools):
            try:
                result = install_skill(t, project_root=skill_root, force=force)
            except FileExistsError as exc:
                click.echo(f"{t.display}: {exc}", err=True)
                skill_errors = True
                continue
            try:
                shown = result.path.relative_to(root)
            except ValueError:
                shown = result.path
            verb = "Updated" if result.overwritten else "Installed"
            click.echo(f"{verb} bora skill for {t.display} → {shown}")

    click.echo("\nDev project scaffolded. Next steps:")
    click.echo("  1. Edit docs/ai/Project.md to describe what you're building.")
    click.echo("  2. Edit docs/ai/Architecture.md once design takes shape.")
    click.echo("  3. Create your first ticket: bora dev ticket new \"<title>\"")

    if skill_errors:
        sys.exit(1)


# =============================================================================
# dev ticket
# =============================================================================


@dev.group()
def ticket() -> None:
    """Manage tickets."""


@ticket.command("new")
@click.argument("title")
@click.option(
    "--type", "ticket_type",
    type=click.Choice(sorted(VALID_TYPES)),
    default="feature", show_default=True,
)
@click.option("--priority", type=click.Choice(sorted(VALID_PRIORITIES)), default="medium", show_default=True)
@click.option("--parent", default="", help="Parent ticket id (for child tickets).")
@click.option("--no-edit", is_flag=True, help="Don't open the new ticket in $EDITOR.")
def ticket_new(title: str, ticket_type: str, priority: str, parent: str, no_edit: bool) -> None:
    """Create a new ticket."""
    root = require_repo_root()
    if parent:
        parent_ticket = find_ticket(tickets_dir(root), parent)
        if parent_ticket is None:
            click.echo(f"Error: parent ticket not found: {parent}", err=True)
            sys.exit(1)
        parent = parent_ticket.id
    path = create_ticket(tickets_dir(root), title=title, ticket_type=ticket_type, priority=priority, parent=parent)
    click.echo(f"Created {path.relative_to(root)}")
    if not no_edit:
        _open_in_editor(path)
    _regenerate_status(root)


@ticket.command("list")
@click.option("--status", type=click.Choice(sorted(VALID_STATUSES)), help="Filter by status.")
@click.option("--type", "ticket_type", type=click.Choice(sorted(VALID_TYPES)), help="Filter by type.")
@click.option("--priority", type=click.Choice(sorted(VALID_PRIORITIES)), help="Filter by priority.")
@click.option("--blocked", is_flag=True, help="Show only tickets with unfinished dependencies.")
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
    """Update a frontmatter field on a ticket."""
    root = require_repo_root()
    t = find_ticket(tickets_dir(root), ticket_id)
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
        parent = find_ticket(tickets_dir(root), value)
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
    _regenerate_status(root)


@ticket.command("note")
@click.argument("ticket_id")
@click.argument("text")
def ticket_note(ticket_id: str, text: str) -> None:
    """Append a dated entry to a ticket's body Notes section."""
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
            f"Error: invalid subtask status {status!r}. Expected one of {sorted(VALID_SUBTASK_STATUSES)}",
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
# dev status
# =============================================================================


@dev.command("status")
def dev_status() -> None:
    """Regenerate Tasks.md from current ticket state."""
    root = require_repo_root()
    path = write_tasks_md(root)
    click.echo(f"Wrote {path.relative_to(root)}")


# =============================================================================
# dev context
# =============================================================================


@dev.command("context")
@click.option("--budget", type=int, default=None, help="Maximum approximate token count.")
def dev_context(budget: Optional[int]) -> None:
    """Print briefing content for a fresh model session.

    Pipe to your clipboard or paste into a chat to brief a model:
        bora dev context | pbcopy
        bora dev context --budget 8000
    """
    root = require_repo_root()
    content = assemble_context(root, budget=budget)
    click.echo(content, nl=False)
    if budget is not None:
        click.echo(f"\n[~{estimate_tokens(content)} tokens, budget {budget}]", err=True)


# =============================================================================
# dev lint
# =============================================================================


@dev.command("lint")
def dev_lint() -> None:
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
# dev decision
# =============================================================================


@dev.group()
def decision() -> None:
    """Manage architecture decisions."""


@decision.command("new")
@click.argument("title")
def decision_new(title: str) -> None:
    """Append a new decision entry to Architecture.md and open it."""
    root = require_repo_root()
    arch_path = root / ARCHITECTURE_FILE
    if not arch_path.exists():
        click.echo(f"Error: {ARCHITECTURE_FILE} does not exist. Run `bora dev init` first.", err=True)
        sys.exit(1)
    today = date.today().isoformat()
    entry = (
        f"\n### {today} — {title}\n\n"
        "**What was decided:** \n\n"
        "**Alternatives considered:** \n\n"
        "**Reasoning:** \n"
    )
    existing = arch_path.read_text(encoding="utf-8")
    if not existing.endswith("\n"):
        existing += "\n"
    arch_path.write_text(existing + entry, encoding="utf-8")
    click.echo(f"Appended decision entry to {ARCHITECTURE_FILE}")
    _open_in_editor(arch_path)


# =============================================================================
# dev skill
# =============================================================================


@dev.group()
def skill() -> None:
    """Install or remove the bora skill for AI coding tools."""


@skill.command("install")
@click.argument("tool", type=click.Choice(_TOOL_CHOICES, case_sensitive=False))
@click.option("--project", is_flag=True, help="Install into the current repo instead of user level.")
@click.option("--force", is_flag=True, help="Overwrite an existing SKILL.md even if it isn't ours.")
def skill_install(tool: str, project: bool, force: bool) -> None:
    """Install the bora skill for an AI tool (claude, opencode, all)."""
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
    """Scaffold a write profile project (AGENTS.md, doc/ai/, Summary.md)."""
    init_writer_project(Path.cwd(), force=force)


# =============================================================================
# write chapter
# =============================================================================


@write.command("chapter")
@click.argument("name")
def write_chapter(name: str) -> None:
    """Scaffold a new chapter directory with manuscript, planning, and research files."""
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
    """Install or remove write-profile skills (e.g. Obsidian vault integration)."""


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
