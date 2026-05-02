"""Install and uninstall the bora skill for AI coding tools.

Both Claude Code and OpenCode (and several other tools) discover skills as
directories containing a `SKILL.md` file. The format is identical across
tools; only the install location differs. This module owns the template
and the per-tool path registry.
"""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# A marker we look for in an existing SKILL.md before agreeing to remove it.
# Conservative: we only manage skills we wrote ourselves.
_SKILL_NAME_RE = re.compile(r"^name:\s*bora\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Tool:
    """A target tool that supports SKILL.md-style skills."""

    key: str           # CLI identifier, lowercase
    display: str       # Human-readable name for messages
    global_dir: Path   # Where ~/-level skills live for this tool
    project_dir: Path  # Where repo-local skills live for this tool


def _opencode_global_root() -> Path:
    """Resolve OpenCode's global config dir, honoring $XDG_CONFIG_HOME."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "opencode"


TOOLS: dict[str, Tool] = {
    "claude": Tool(
        key="claude",
        display="Claude Code",
        global_dir=Path.home() / ".claude" / "skills",
        project_dir=Path(".claude") / "skills",
    ),
    "opencode": Tool(
        key="opencode",
        display="OpenCode",
        global_dir=_opencode_global_root() / "skills",
        project_dir=Path(".opencode") / "skills",
    ),
}

SKILL_NAME = "bora"


def skill_path(tool: Tool, *, project_root: Optional[Path] = None) -> Path:
    """Return the full path to a tool's bora skill directory."""
    if project_root is not None:
        return (project_root / tool.project_dir / SKILL_NAME).resolve()
    return tool.global_dir / SKILL_NAME


def is_bora_skill(skill_md: Path) -> bool:
    """True if a SKILL.md file declares name: bora in its frontmatter."""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return False
    return bool(_SKILL_NAME_RE.search(text))


@dataclass
class InstallResult:
    tool: Tool
    path: Path
    overwritten: bool


def install(tool: Tool, *, project_root: Optional[Path] = None, force: bool = False) -> InstallResult:
    """Install the bora skill for `tool`. Raises FileExistsError if a non-bora
    SKILL.md is already at the target and `force` is False."""
    target_dir = skill_path(tool, project_root=project_root)
    skill_md = target_dir / "SKILL.md"

    overwritten = skill_md.exists()
    if overwritten and not force and not is_bora_skill(skill_md):
        raise FileExistsError(
            f"A different SKILL.md already exists at {skill_md}. "
            f"Use --force to overwrite."
        )

    target_dir.mkdir(parents=True, exist_ok=True)
    skill_md.write_text(BORA_SKILL_MD, encoding="utf-8")
    return InstallResult(tool=tool, path=skill_md, overwritten=overwritten)


@dataclass
class UninstallResult:
    tool: Tool
    path: Path
    removed: bool
    reason: str = ""  # populated when removed=False


def uninstall(tool: Tool, *, project_root: Optional[Path] = None, force: bool = False) -> UninstallResult:
    """Remove the bora skill directory for `tool` if we own it.

    Refuses to delete a SKILL.md that doesn't declare `name: bora` unless
    `force` is True.
    """
    target_dir = skill_path(tool, project_root=project_root)
    skill_md = target_dir / "SKILL.md"

    if not target_dir.exists():
        return UninstallResult(tool=tool, path=target_dir, removed=False, reason="not installed")

    if skill_md.exists() and not is_bora_skill(skill_md) and not force:
        return UninstallResult(
            tool=tool,
            path=target_dir,
            removed=False,
            reason="SKILL.md at this path is not bora's (use --force to remove anyway)",
        )

    shutil.rmtree(target_dir)
    return UninstallResult(tool=tool, path=target_dir, removed=True)


@dataclass
class Status:
    tool: Tool
    scope: str         # "global" or "project"
    path: Path
    installed: bool
    is_ours: bool      # True if installed AND looks like our SKILL.md


def list_status(*, project_root: Optional[Path] = None) -> list[Status]:
    """Return install status for every known tool, both global and project scopes
    (project only included if `project_root` is provided)."""
    out: list[Status] = []
    for tool in TOOLS.values():
        gpath = skill_path(tool)
        gskill = gpath / "SKILL.md"
        out.append(Status(
            tool=tool,
            scope="global",
            path=gpath,
            installed=gskill.exists(),
            is_ours=is_bora_skill(gskill),
        ))
        if project_root is not None:
            ppath = skill_path(tool, project_root=project_root)
            pskill = ppath / "SKILL.md"
            out.append(Status(
                tool=tool,
                scope="project",
                path=ppath,
                installed=pskill.exists(),
                is_ours=is_bora_skill(pskill),
            ))
    return out


# ---------------------------------------------------------------------------
# Skill template
# ---------------------------------------------------------------------------

BORA_SKILL_MD = """---
name: bora
description: Use this skill when working in a project that contains an `AGENTS.md` referring to bora, a `docs/ai/` directory with `Project.md` and `Tasks.md`, or `docs/ai/tickets/`. bora is a CLI for managing tickets, briefings, and architecture decisions for human-AI coding collaboration. Use this skill to read the project briefing, create or update tickets, regenerate the task dashboard, and validate frontmatter.
---

# bora

bora is a small CLI that maintains a structured set of Markdown + YAML
files for human-AI coding collaboration. The files live in version control
and are designed so any AI agent can read them to get oriented before
writing code.

## When to use this skill

Load this skill when you see any of:

- An `AGENTS.md` at the repo root mentioning bora.
- A `docs/ai/` directory with `Project.md`, `Architecture.md`, or `Tasks.md`.
- A `docs/ai/tickets/` directory containing `*.md` ticket files.
- The user asks you to create a ticket, update task status, or brief
  yourself on the project.

If `bora` is not on `PATH`, suggest the user install it
(`pipx install bora` or `pip install --user bora`) and fall back to
reading and editing the files directly using their conventions.

## Briefing sequence (do this first in any new session)

Read in this order:

1. `AGENTS.md` — operating instructions for AI agents on this project.
2. `docs/ai/Project.md` — what is being built and why.
3. `docs/ai/Architecture.md` — design decisions and decision log.
4. `docs/ai/Tasks.md` — current state of work.
5. Specific files in `docs/ai/tickets/` as the active work demands.

If your context budget is tight, run `bora context --budget <tokens>` to
get a token-bounded briefing instead.

## Core conventions (do not violate)

- **`Tasks.md` is auto-generated.** Never hand-edit it. Update tickets
  and run `bora status` to regenerate.
- **Ticket IDs are `YYYYMMDD-NN-slug`.** The CLI generates them. Never
  pick your own — always create tickets via `bora ticket new "<title>"`.
- **Decisions append to `Architecture.md`.** Don't rewrite history; add
  a new dated entry when the design evolves (or use `bora decision new`).
- **After writing to any ticket file, run `bora lint`.** Don't trust
  your own YAML output — validation catches frontmatter errors before
  they corrupt project state.
- **Subtasks live in two places by design.** Major subtasks go in the
  ticket's frontmatter `subtasks` list (queryable, aggregated in
  `Tasks.md`). Small subtasks are body checkboxes (counted but not
  aggregated by id).

## Command surface

| Command | Purpose |
| --- | --- |
| `bora init` | Scaffold AGENTS.md and docs/ai/ in the current dir. |
| `bora context [--budget N]` | Print the full briefing, optionally token-bounded. |
| `bora ticket new "<title>"` | Create a new ticket. Options: `--type`, `--priority`, `--parent`. |
| `bora ticket list` | List tickets. Filters: `--status`, `--type`, `--priority`, `--blocked`. |
| `bora ticket show <id>` | Print a ticket's contents. Fuzzy id match supported. |
| `bora ticket set <id> <field> <value>` | Update a frontmatter field (status, priority, etc.). |
| `bora ticket subtask <id> <sub-id> <status>` | Update a frontmatter subtask's status. |
| `bora ticket note <id> "<text>"` | Append a dated entry to the body Notes section. |
| `bora status` | Regenerate `Tasks.md`. |
| `bora lint` | Validate frontmatter and cross-references. |
| `bora decision new "<title>"` | Append a templated decision entry to `Architecture.md`. |

Run `bora <command> --help` for full options on any command.

## Workflows

### Starting a new feature
1. Read `Project.md` and `Architecture.md` to confirm scope.
2. Propose an implementation plan in conversation with the human.
3. Once agreed, create one or more tickets via `bora ticket new`.
4. If the feature decomposes, use `--parent` to link child tickets.
5. Populate each ticket's Description, Acceptance criteria, Context, and
   Subtasks (frontmatter for major ones; body checkboxes for small ones).

### Resuming work on an existing ticket
1. Run `bora ticket show <id>` (or read the file).
2. Check the latest entry in the body Notes section.
3. If status is `todo`, set it to `in-progress`:
   `bora ticket set <id> status in-progress`.
4. Append a dated Notes entry when you make meaningful progress.

### Marking a ticket complete
1. Verify all acceptance criteria are met.
2. Verify all body checkboxes are checked.
3. Run `bora ticket set <id> status done`. The `closed` date populates
   automatically.

## Frontmatter reference

Ticket frontmatter fields:

- `id` — `YYYYMMDD-NN-slug`. Set by `bora ticket new`; do not change.
- `title` — short human-readable title.
- `type` — `feature` | `bug` | `chore` | `spike`.
- `priority` — `high` | `medium` | `low`.
- `status` — `todo` | `in-progress` | `blocked` | `done`.
- `created`, `updated`, `closed` — ISO dates. Managed by the CLI.
- `notes` — one-line current state, shown in `Tasks.md`.
- `parent` — single ticket id, or empty.
- `depends_on` — list of ticket ids that must be `done` first.
- `subtasks` — list of `{id, title, status}` for major subtasks.
"""
