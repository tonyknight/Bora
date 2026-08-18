"""Skill pack templates installed by `bora dev skill install` and `bora dev upgrade`."""

from __future__ import annotations

from .routing import DEFAULT_SKILL_TIERS

PACK_SKILLS = (
    "bora",
    "bora-plan",
    "bora-tdd",
    "bora-execute",
    "bora-design",
    "bora-worktree",
    "bora-review",
    "bora-debug",
    "bora-verify",
    "bora-finish",
)

PACK_SKILL_NAMES_RE = (
    r"bora(?:-(?:plan|tdd|execute|design|worktree|review|debug|verify|finish))?"
)

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

## Skill check (load before acting)

Before architecture, Requirements, tickets, a plan, execute, or code,
load the matching skill when it applies:

| Skill | When |
| --- | --- |
| `bora-design` | Briefing exists; Requirements still placeholder or architecture not agreed |
| `bora-plan` | Ticket needs `## Implementation plan` before code |
| `bora-tdd` | Implementing a plan task; expected RED on a new test |
| `bora-execute` | Requirements approved; "go"; or resuming the board |
| `bora-worktree` | Start of execute; isolation consent (via execute) |
| `bora-verify` | Before claiming task/ticket/board complete or finish |
| `bora-review` | After last plan task on a ticket; before `done` |
| `bora-debug` | Unexpected verify/build failure (not expected RED) |
| `bora-finish` | Board complete; project suite verified |

## Briefing sequence (do this first in any new session)

Read in this order:

1. `AGENTS.md` (root — operating instructions)
2. The human-referenced project briefing:
   `docs/ai/<path>/(YYYY-MM-DD) {ProjectName}.md`
3. Load `bora-design`. Discuss architecture before writing Requirements.
   Do not skip this conversation. Do not fill Requirements from the
   briefing alone.
4. After agreement, author/update:
   `docs/ai/<path>/(YYYY-MM-DD) {ProjectName} Requirements.md`
5. `docs/ai/<path>/Status.md`  (read only — never hand-edit)
6. When implementing: create tickets from Requirements Tasks Breakdown.
   After "go", load `bora-execute` (worktree, plan, tdd, verify, review,
   finish). Write `## Implementation plan` on each ticket (`bora-plan`).
7. `docs/ai/<path>/tickets/<id>.md` as active work demands
8. If budget-constrained, run `bora dev context <path> --budget N`

## Core conventions (do not violate)

- **`Status.md` is auto-generated.** Never hand-edit it.
- **Ticket IDs** via `bora dev ticket new <project_path> "<title>"`.
- **Plan on the ticket.** Never a `plans/` folder.
- **After "go", load `bora-execute`.** Walk the whole board. Never ask
  "should I continue?" Show completed vs remaining after each ticket.
- **Commit criteria** before `done` or commit:
  `{ticket-id} {task-id}: {title}`.
- **After any ticket write:** `bora dev lint` then `bora dev status`.

See `AGENTS.md` for full command surface and frontmatter reference.

## Session routing (opt-in)

If the current project's briefing has `routing: true` and the repo
catalog (`.bora/models.yaml`) is enabled, resolve **this session**
before spawning subagents:

1. Collect the model ids this host can actually run (from the harness,
   not from the `bora` CLI).
2. Write them to a temp file, one per line, then run
   `bora dev routing resolve <project_path> --host <cursor|claude|opencode> --available <file>`.
3. If a tier result is ASK, ask the human. Do not invent a model id.
4. Pass matched host slugs into subagent starts when the host API
   accepts a model id.
5. After unique matches, update briefing `routing_cache` for this host.
   Cache is a hint only; resolve again next session.
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
test, confirm the failure is the right one) → GREEN (minimal code) →
load **`bora-verify`** (run the task's Verify command in this turn) →
commit `{ticket-id} {task-id}: {title}` → next task.

Do not invent `npm test` if the plan names `pytest` or `xcodebuild`.
Expected RED on a new test is **not** `bora-debug`. On unexpected
failure, load `bora-debug` before a second rewrite.

After the ticket is complete, return to `bora-execute` (do not ask what
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
at a time.

## On start

1. Load **`bora-worktree`** (consent once; record `origin_branch` on
   the briefing frontmatter).
2. If the briefing has `routing: true` and the repo catalog is enabled,
   resolve this session (`bora dev routing resolve` with an injected
   available-model list). ASK means ask the human. Pass slugs to
   subagents when the host supports it. Update `routing_cache` after
   unique matches; it is a hint only.

## Per ticket

1. `bora-plan` if `## Implementation plan` is missing or empty.
2. `bora-tdd` for each open `T0n`:
   - unexpected verify/build failure → `bora-debug`, then continue or block
   - each task done → `bora-verify` (task Verify line)
3. After last task: `bora-verify` (ticket scope) → **`bora-review`**
4. Mark `done` only if review is clean or minors-only.
5. `bora dev status` — **show** completed vs remaining → next ticket.

Never ask "should I continue?"

## Board complete

`bora-verify` (project suite from Requirements) → **`bora-finish`**.

## Stop when

Board complete, nothing unblocked remains, debug exhausted on same
hypothesis, plan collides with Requirements, or the human interrupted.

Resume from Status.md, `current_task`, and `git log --grep=<ticket-id>`.

Routine `bora-verify` is economy-class activity. Unexpected failure
loads `bora-debug` (premium). Do not implement automatic model switching.

## Optional subagent mode

If the harness can dispatch subagents and the human did not forbid them:
one implementer **per ticket** (not per `T0n`, not two tickets in
parallel on shared files). Controller keeps board, Status.md, and
`bora-review`. Implementer gets project path, ticket path, Requirements
path, commit contract, TDD iron law — no chat history. On DONE,
controller runs `bora-review`. If subagents unavailable, in-session
execute is correct.
"""

BORA_DESIGN_SKILL_MD = """---
name: bora-design
description: Use when a bora project briefing exists and architecture is not yet agreed; when the Requirements file is still a placeholder; or when the user wants to discuss design before tickets. Do not use after Requirements are approved and execution has started, unless the user explicitly reopens design.
---

# bora-design

Brainstorming with **output = the dated Requirements file**, not a
separate spec directory.

1. Read the briefing first.
2. Ask questions (prefer one at a time). Propose 2–3 approaches with a
   recommendation.
3. Present design in sections scaled to complexity; wait for agreement
   on contested sections (architecture, testing/commit criteria, Tasks
   Breakdown).
4. Only then fill Requirements: architecture, requirements, acceptance,
   **Testing requirements** (name real commands: `xcodebuild`, `pytest`, …),
   commit criteria, Tasks Breakdown, risks, open questions. Bump
   `last_reviewed`.

Hard gate: no tickets, no code, no `bora-execute` until the human
approves Requirements. YAGNI: do not invent tickets for non-goals.

If the project is too large for one Requirements file, split into
another `bora dev init` path — do not create a spec subdirectory.

If execution finds a Requirements hole, stop execute and reopen design
with the human — do not invent architecture on the ticket.
"""

BORA_WORKTREE_SKILL_MD = """---
name: bora-worktree
description: Use when starting or resuming bora-execute on a bora project; when the user asks for an isolated branch or worktree; or before the first production commit of a project-level go. Do not create a nested worktree if already isolated.
---

# bora-worktree

Detect existing isolation → native harness tool → `git worktree` fallback.
Never fight the harness.

## Record origin branch

Before creating isolation, record the checked-out branch (or detached
HEAD + short SHA) on the project briefing frontmatter:

```yaml
origin_branch: feature/share-extension
```

`bora-finish` option 1 merges **only** to `origin_branch` — never
assume `main`/`master`.

## Consent (once per project)

If no stored preference, ask: isolate this project's work?

- Yes → create isolation; set `worktree: true` on briefing frontmatter
- No → work in place; set `worktree: false`

Do not re-ask later tickets in the same execute run.

## Execute branch

`bora/<project_path-as-slug>` (e.g. `bora/photoapp-ios-share-extension`).
Reuse if it exists (resume). Ticket commits land here; integration
lands on `origin_branch`.

Worktree directory: prefer `.worktrees/` at repo root if gitignored;
else harness default. Do not commit the worktree.

Do not start execute on `main`/`master` without explicit consent.

Cleanup is **`bora-finish`** (human-approved), not this skill.
"""

BORA_REVIEW_SKILL_MD = """---
name: bora-review
description: Use when a bora ticket's plan tasks are all checked and before marking the ticket done; when the user asks to review a ticket; or when bora-execute has just finished a ticket's last commit. Do not use for architecture review (that is Requirements / bora-design).
---

# bora-review

Review **this ticket's commit range**: `git log --grep=<ticket-id>`
from first `T01` commit through `HEAD` (no uncommitted work).

**Spec:** Requirements (matching items) + ticket acceptance criteria +
`## Implementation plan` (files named vs files touched).

**Quality:** YAGNI, TDD evidence (RED then GREEN in history or Notes),
commit messages `{ticket-id} {task-id}: {title}`.

**Verdicts:** Critical / Important / Minor.

- Critical or Important: do **not** mark `done`; do not start the next
  ticket. Fix via `bora-tdd` / `bora-debug` or ask the human.
- Minor: ticket Notes.

If the harness has subagents, dispatch a **fresh** reviewer with the
diff. Otherwise review in-session; still do not skip.

Append a short `## Review` subsection on the ticket (date, verdict,
findings). No `reviews/` folder.

Human pasted review comments: read the diff, fix Critical/Important.
"""

BORA_DEBUG_SKILL_MD = """---
name: bora-debug
description: Use when a plan-task verify command fails, a build fails, or behavior is unexpected during bora execute or TDD; before proposing a second implementation attempt. Do not use for the expected RED failure of a newly written test.
---

# bora-debug

Four phases: investigate → pattern analysis → hypothesis → fix.
No fix without root cause.

Expected RED (new test failed as designed) is **`bora-tdd`**, not this
skill.

Record root cause in ticket Notes. If the plan task is wrong, amend the
plan (add `Tnn`; do not renumber committed ids).

After a fix, `bora-verify` that task's command, then continue execute.

If root cause is a Requirements hole, **stop execute**, reopen
`bora-design` with the human.

A second failure on the same hypothesis still stops and blocks the ticket.

Unexpected failure diagnosis is premium-class activity.
"""

BORA_VERIFY_SKILL_MD = """---
name: bora-verify
description: Use when marking a bora plan task complete, before marking a ticket done, before claiming tests pass, or before bora-finish. Do not use as a substitute for TDD's RED step.
---

# bora-verify

Iron law: no completion claim without a **fresh** run of the named
command in this turn.

| Gate | Command |
| --- | --- |
| Plan task complete | That task's **Verify:** line |
| Ticket `done` | Task verifies + acceptance criteria + any extra "ticket done" command in Requirements Commit criteria |
| Board complete / finish | Project suite from Requirements **Testing requirements** |

Paste or quote enough output to show pass/fail. "Should pass" is a
failure of this skill.

`bora-tdd` and `bora-finish` both require this skill.

Routine verification is economy-class activity.
"""

BORA_FINISH_SKILL_MD = """---
name: bora-finish
description: Use when a bora project has no remaining unblocked tickets (all done, or only blocked the human accepted as out of scope), verification of the project suite has passed, and the user needs to decide how to integrate. Use also when the user says the work is done, merge, or PR. Do not use after a single ticket if others remain.
---

# bora-finish

1. Run **`bora-verify`** on the project suite. Failures: no menu.
2. Read `origin_branch` from the briefing (set by `bora-worktree`).
   Do not default to `main`. Ask if missing or ambiguous.

```
Board complete for <project_path>. What would you like to do?

1. Merge back to <origin_branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
```

**Option 1:** checkout `<origin_branch>`, merge `bora/<slug>` into it
only. Run post-merge verify if Requirements name one.

**After option 1, if Bora created a worktree this run**, offer cleanup:

```
Merge complete on <origin_branch>. Remove the bora worktree and execute
branch to restore the repo?

1. Yes — remove worktree + delete bora/<slug> (only what this session created)
2. No — leave worktree/branch in place
```

Yes: remove worktree dir, delete merged `bora/<slug>`, leave checkout on
`origin_branch`. Never remove human-created worktrees/branches.

Detached HEAD / external worktree: options 2 and 3 only.

Options 2–3: no auto-clean; offer cleanup only if the human asks.

Do not mark tickets `done` here. Note merge/PR URL on a ticket if useful.
Agent runs `git` / `gh` — no `bora dev finish` command.
"""

SKILL_TEMPLATES: dict[str, str] = {
    "bora": BORA_SKILL_MD,
    "bora-plan": BORA_PLAN_SKILL_MD,
    "bora-tdd": BORA_TDD_SKILL_MD,
    "bora-execute": BORA_EXECUTE_SKILL_MD,
    "bora-design": BORA_DESIGN_SKILL_MD,
    "bora-worktree": BORA_WORKTREE_SKILL_MD,
    "bora-review": BORA_REVIEW_SKILL_MD,
    "bora-debug": BORA_DEBUG_SKILL_MD,
    "bora-verify": BORA_VERIFY_SKILL_MD,
    "bora-finish": BORA_FINISH_SKILL_MD,
}

_ADVISORY_ROUTING_NOTE = (
    "The `model_tier` field is an advisory hint for the host. "
    "Bora does not choose models."
)


def render_pack_skill(name: str) -> str:
    """Return installed SKILL.md text with `model_tier` from Python defaults."""
    text = SKILL_TEMPLATES[name]
    if not text.startswith("---\n"):
        raise ValueError(f"{name} skill template is missing YAML frontmatter")
    rest = text[4:]
    close = rest.find("\n---\n")
    if close < 0:
        raise ValueError(f"{name} skill template is missing a closing frontmatter fence")
    frontmatter = rest[:close]
    body = rest[close + len("\n---\n") :]
    if not frontmatter.endswith("\n"):
        frontmatter += "\n"
    frontmatter += f"model_tier: {DEFAULT_SKILL_TIERS[name]}\n"
    heading = f"# {name}\n"
    idx = body.find(heading)
    if idx >= 0:
        insert_at = idx + len(heading)
        body = body[:insert_at] + "\n" + _ADVISORY_ROUTING_NOTE + "\n" + body[insert_at:]
    else:
        body = "\n" + _ADVISORY_ROUTING_NOTE + "\n" + body.lstrip("\n")
    return f"---\n{frontmatter}---\n{body}"
