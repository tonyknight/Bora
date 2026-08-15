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
PACK_SKILLS = ("bora", "bora-plan", "bora-tdd", "bora-execute")
_OWNED_NAME_RE = re.compile(
    r"^name:\s*(bora|bora-plan|bora-tdd|bora-execute)\s*$",
    re.MULTILINE,
)


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


def pack_root(tool: Tool, *, project_root: Optional[Path] = None) -> Path:
    """Directory that holds the skill pack (`bora/`, `bora-plan/`, …)."""
    if project_root is not None:
        return (project_root / tool.project_dir).resolve()
    return tool.global_dir


def skill_path(tool: Tool, *, project_root: Optional[Path] = None) -> Path:
    """Return the full path to a tool's bootstrap `bora` skill directory."""
    return pack_root(tool, project_root=project_root) / "bora"


def is_bora_skill(skill_md: Path) -> bool:
    """True if a SKILL.md file declares a bora-owned name in its frontmatter."""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return False
    return bool(_OWNED_NAME_RE.search(text))


@dataclass
class InstallResult:
    tool: Tool
    path: Path
    overwritten: bool


def install(tool: Tool, *, project_root: Optional[Path] = None, force: bool = False) -> InstallResult:
    """Install the bora skill pack for `tool`. Raises FileExistsError if a
    non-bora SKILL.md is already at a pack path and `force` is False."""
    root = pack_root(tool, project_root=project_root)
    bora_md = root / "bora" / "SKILL.md"
    overwritten = bora_md.exists()
    for name in PACK_SKILLS:
        skill_md = root / name / "SKILL.md"
        if skill_md.exists() and not force and not is_bora_skill(skill_md):
            raise FileExistsError(
                f"A different SKILL.md already exists at {skill_md}. "
                f"Use --force to overwrite."
            )

    for name in PACK_SKILLS:
        target_dir = root / name
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "SKILL.md").write_text(SKILL_TEMPLATES[name], encoding="utf-8")
    return InstallResult(tool=tool, path=bora_md, overwritten=overwritten)


@dataclass
class UninstallResult:
    tool: Tool
    path: Path
    removed: bool
    reason: str = ""  # populated when removed=False


def uninstall(tool: Tool, *, project_root: Optional[Path] = None, force: bool = False) -> UninstallResult:
    """Remove the bora skill pack for `tool` if we own it."""
    root = pack_root(tool, project_root=project_root)
    bora_dir = root / "bora"
    bora_md = bora_dir / "SKILL.md"

    any_present = any((root / name).exists() for name in PACK_SKILLS)
    if not any_present:
        return UninstallResult(tool=tool, path=bora_dir, removed=False, reason="not installed")

    for name in PACK_SKILLS:
        skill_md = root / name / "SKILL.md"
        if skill_md.exists() and not is_bora_skill(skill_md) and not force:
            return UninstallResult(
                tool=tool,
                path=root / name,
                removed=False,
                reason="SKILL.md at this path is not bora's (use --force to remove anyway)",
            )

    for name in PACK_SKILLS:
        target = root / name
        if target.exists():
            shutil.rmtree(target)
    return UninstallResult(tool=tool, path=bora_dir, removed=True)


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
description: Use when the repo has an AGENTS.md referring to bora, a docs/ai hierarchical project, or when the user points at a project briefing. Use at the start of a session in a bora project before reading or editing those files.
---

# bora

bora is a small CLI that maintains a structured set of Markdown + YAML
files for human-AI coding collaboration. The files live in version control
and are designed so any AI agent can read them to get oriented before
writing code.

Each software project lives under `docs/ai/<Codebase>/<Target>/<Project>/`.
Multiple projects may coexist. The human references one project's dated
briefing when starting a session; that directory is the only scope.

## When to use this skill

Load this skill when you see any of:

- An `AGENTS.md` at the repo root mentioning bora.
- A `docs/ai/<Codebase>/<Target>/<Project>/` directory with a dated
  briefing, a dated Requirements file, or `Status.md`.
- A `docs/ai/<path>/tickets/` directory containing `*.md` ticket files.
- The user asks you to create a ticket, update task status, or brief
  yourself on the project.

If `bora` is not on `PATH`, suggest the user install it
(`pipx install bora` or `pip install --user bora`) and fall back to
reading and editing the files directly using their conventions.

## Briefing sequence (do this first in any new session)

Read in this order:

1. `AGENTS.md` (root — this file's companion operating instructions)
2. The human-referenced project briefing:
   `docs/ai/<path>/(YYYY-MM-DD) {ProjectName}.md`
3. Discuss architecture with the human before writing Requirements.
   Do not skip this conversation. Do not fill in the Requirements
   file from Project.md alone.
4. After agreement, author/update:
   `docs/ai/<path>/(YYYY-MM-DD) {ProjectName} Requirements.md`
5. `docs/ai/<path>/Status.md`  (read only — never hand-edit)
6. When implementing: create tickets from the Requirements
   Tasks Breakdown. Tickets may be worked by one or more agents.
7. `docs/ai/<path>/tickets/<id>.md` as the active work demands
8. If budget-constrained, run `bora dev context <project_path> --budget N`

## Scope guardrail

**Scope guardrail:** The human will reference the correct `docs/ai/<path>/(YYYY-MM-DD) {ProjectName}.md` when starting the session. Only read and write files inside that project's directory (`docs/ai/<path>/` and its `tickets/`). Do not operate on other `docs/ai/<other>/` projects, the legacy flat `docs/ai/Project.md`, or the repo root unless the human explicitly references them. `Status.md` is per-project only — do not expect or create a root `docs/ai/Status.md` or `docs/ai/Tasks.md` aggregation. All `bora dev` commands require the explicit `<project_path>` argument to enforce this.

## Layout

```
docs/
  ai/
    <Codebase>/
      <Target>/
        <Project>/
          (YYYY-MM-DD) {ProjectName}.md
          (YYYY-MM-DD) {ProjectName} Requirements.md
          Status.md
          tickets/
            .gitkeep
            <id>.md
```

## Core conventions (do not violate)

- **`Status.md` is auto-generated.** Never hand-edit it. Update tickets
  and run `bora dev status <project_path>` to regenerate.
- **Ticket IDs are `YYYYMMDD-NN-slug`.** The CLI generates them. Never
  pick your own — always create tickets via
  `bora dev ticket new <project_path> "<title>"`.
- **Decisions go in the Requirements file.** There is no decision
  command. After agreeing with the human, edit Architecture or Open
  questions in the dated Requirements file.
- **After writing to any ticket file, run `bora dev lint <project_path>`**
  then `bora dev status <project_path>`. Don't trust your own YAML
  output — validation catches frontmatter errors before they corrupt
  project state.
- **Subtasks live in two places by design.** Major subtasks go in the
  ticket's frontmatter `subtasks` list (queryable, aggregated in
  `Status.md`). Small subtasks are body checkboxes (counted but not
  aggregated by id).
- **Commit criteria before done or commit.** Do not mark a ticket or
  subtask `done` and do not git commit until completion tests pass, the
  change meets the matching requirement, and build tests pass. Commit
  message: `{ticket-id} {task-id}: {title}`.
- **Plan on the ticket.** `## Implementation plan` on the ticket (`bora-plan`).
  Never put the commit script in Requirements or a `plans/` folder.
- **After "go", load `bora-execute`.** Walk remaining tickets. Show
  completed vs remaining after each. Never ask "should I continue?"
- **Skill check.** Before architecture, Requirements, tickets, a plan,
  execute, or code, load `bora-plan`, `bora-tdd`, or `bora-execute`
  when they match. The human runs `init`, `skill install`, and
  `upgrade`; you run ticket/plan/status/lint.

## Command surface

| Command | Purpose |
| --- | --- |
| `bora dev init <project_path>` | Scaffold AGENTS.md (if missing) and `docs/ai/<project_path>/`. |
| `bora dev context <project_path> [--budget N]` | Print the project briefing, optionally token-bounded. |
| `bora dev ticket new <project_path> "<title>"` | Create a new ticket. Options: `--type`, `--priority`, `--parent`. |
| `bora dev ticket list <project_path>` | List tickets. Filters: `--status`, `--type`, `--priority`, `--blocked`. |
| `bora dev ticket show <project_path> <id>` | Print a ticket's contents. Fuzzy id match supported. |
| `bora dev ticket set <project_path> <id> <field> <value>` | Update a frontmatter field (status, priority, etc.). |
| `bora dev ticket subtask <project_path> <id> <sub-id> <status>` | Update a frontmatter subtask's status. |
| `bora dev ticket note <project_path> <id> "<text>"` | Append a dated entry to the body Notes section. |
| `bora dev status <project_path>` | Regenerate `Status.md`. |
| `bora dev lint <project_path>` | Validate ticket frontmatter and plan sections. |
| `bora dev upgrade` | Refresh managed AGENTS.md and installed skills. |
| `bora dev plan show/set/task <project_path> …` | Read or update a ticket's implementation plan. |

Run `bora dev <command> --help` for full options on any command.
Missing `<project_path>` is an error; there is no active-project fallback.

## Workflows

### Orient, then Requirements, then tickets
1. Read the referenced project briefing and confirm scope with the human.
2. Discuss architecture: components, data model, key flows, constraints,
   non-goals. Propose options; wait for agreement.
3. Write or update `(YYYY-MM-DD) {ProjectName} Requirements.md`. Bump
   `last_reviewed`.
4. Only then create tickets from the Tasks Breakdown:
   `bora dev ticket new <project_path> "<title>"`.
   Use `--parent` when a breakdown item splits.
5. After ticket changes, run `bora dev status <project_path>` so
   `Status.md` reflects current work.

### Resuming work on an existing ticket
1. Run `bora dev ticket show <project_path> <id>` (or read the file).
   Example: `bora dev ticket show QromaCore/Hamburg/Gallery\\ Refactor 20260811-01`
2. Check the latest entry in the body Notes section.
3. If status is `todo`, set it to `in-progress`:
   `bora dev ticket set <project_path> <id> status in-progress`.
4. Append a dated Notes entry when you make meaningful progress.
5. Run `bora dev status <project_path>`. Example:
   `bora dev status QromaCore/Hamburg/Gallery\\ Refactor`.

### Marking a ticket complete
1. Before `bora dev ticket set <project_path> <id> status done` (or
   setting a subtask to `done`), satisfy Commit criteria in the
   Requirements file: completion tests pass, the change meets the
   requirement, and build/tests pass.
2. Verify all acceptance criteria are met and all body checkboxes are
   checked.
3. Then set status done. The `closed` date populates automatically.
4. If the human wants a commit, use message
   `{ticket-id} {task-id}: {title}`. Do not commit if build or
   completion tests failed.

## Frontmatter reference

Tickets live at `docs/ai/<path>/tickets/<id>.md`. Ticket IDs are unique
per-project, not repo-global.

Ticket frontmatter fields:

- `id` — `YYYYMMDD-NN-slug`. Set by
  `bora dev ticket new <project_path> "<title>"`; do not change.
- `title` — short human-readable title.
- `type` — `feature` | `bug` | `chore` | `spike`.
- `priority` — `high` | `medium` | `low`.
- `status` — `todo` | `in-progress` | `blocked` | `done`.
- `created`, `updated`, `closed` — ISO dates. Managed by the CLI.
- `notes` — one-line current state, shown in `Status.md`.
- `parent` — single ticket id, or empty.
- `depends_on` — list of ticket ids that must be `done` first.
- `subtasks` — list of `{id, title, status}` for major subtasks.
- `plan_status` — optional. `draft` | `approved` | `in-progress` | `done` | `blocked`.
- `current_task` — optional. A `Tnn` id from this ticket's implementation plan.
"""

BORA_PLAN_SKILL_MD = """---
name: bora-plan
description: Use when a ticket in a bora project needs an implementation plan before code (Requirements already approved); when the user asks to plan a ticket; or when bora-execute has selected a ticket that has no ## Implementation plan yet.
---

# bora-plan

Write `## Implementation plan` **on that ticket**. Do not create a
`plans/` file. Do not append the commit script to Requirements.

Each task is one commit (`T01`, `T02`, …), with exact files and a
**Verify:** command copied from Requirements Testing requirements.
No placeholders. During `bora-execute`, do not stop for per-ticket
plan approval. If the human is planning a single ticket before "go",
wait for their yes.

Commands: `bora dev plan show|set|task <project_path> <id> …`.
"""

BORA_TDD_SKILL_MD = """---
name: bora-tdd
description: Use when implementing a feature, bugfix, or plan task in a bora project; before writing production code; or before marking a plan task or ticket done.
---

# bora-tdd

No production code without a failing test first. Cycle: RED (write
test, confirm the failure is the right one) → GREEN (minimal code,
run the **task's** Verify command) → commit `{ticket-id} {task-id}:
{title}` → next task.

Do not invent `npm test` if the plan names `pytest` or `xcodebuild`.
Do not mark a task complete on a pass you did not just run. After
the ticket is complete, return to `bora-execute` (do not ask what
next). Exceptions (ask the human): spike tickets, generated code,
pure config/docs.
"""

BORA_EXECUTE_SKILL_MD = """---
name: bora-execute
description: Use when a bora project's Requirements are approved and the user asks to implement, execute, go, or work through the tickets; when resuming a project that still has todo or in-progress tickets; or after a ticket is marked done and other tickets remain.
---

# bora-execute

Walk the **whole ticket board**. Create missing tickets from the
Requirements Tasks Breakdown. Order: skip done; skip blocked; honor
`depends_on`; then priority; then oldest id. One ticket in-progress
at a time. For each ticket: `bora-plan` if needed, then `bora-tdd`.

After each ticket `done`, run `bora dev status` and **show**
completed vs remaining, then start the next ticket. Never ask
"should I continue?"

Stop when the board is complete, nothing unblocked remains,
verification failed twice on the same task, the plan collides with
Requirements, or the human interrupted. Resume from Status.md,
`current_task`, and `git log --grep=<ticket-id>`.
"""

SKILL_TEMPLATES = {
    "bora": BORA_SKILL_MD,
    "bora-plan": BORA_PLAN_SKILL_MD,
    "bora-tdd": BORA_TDD_SKILL_MD,
    "bora-execute": BORA_EXECUTE_SKILL_MD,
}
