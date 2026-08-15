"""Static templates for scaffolded files.

Kept in a single module rather than separate files because they're tightly
coupled to the framework's conventions and shipping them as package data
just adds setup complexity. If they grow large, split them out.
"""

from __future__ import annotations

from datetime import date
import re

import yaml

from .paths import tag_key


AGENTS_TEMPLATE_VERSION = "0.5.0"
MANAGED_END = "<!-- bora-managed:end -->"
MANAGED_START_RE = re.compile(
    r'<!--\s*bora-managed:start\s+version="([^"]+)"\s*-->'
)
MANAGED_END_RE = re.compile(r"<!--\s*bora-managed:end\s*-->")

AGENTS_MD_BODY = """## Philosophy

This project uses a structured collaboration framework. Documentation in
`docs/ai/<Codebase>/<Target>/<Project>/` is your per-project shared
workspace. Multiple projects may coexist under `docs/ai/`. You read the
referenced project to get oriented, you propose updates as work
progresses, and you treat that project's files as the source of truth
about its state.

The project briefing and Requirements files are dated and named after
the project: `(YYYY-MM-DD) {ProjectName}.md` and
`(YYYY-MM-DD) {ProjectName} Requirements.md`. `Status.md` is
auto-generated — never hand-edit it.

Three principles:

1. **`Status.md` is auto-generated.** Never edit it directly. Update
   tickets instead, then run `bora dev status <project_path>` to
   regenerate.
2. **The project briefing and Requirements file are collaborative.**
   Discuss architecture with the human before writing Requirements.
   Propose changes in conversation; don't edit silently.
3. **Tickets are where work happens.** Create them from the Requirements
   Tasks Breakdown only after architecture is agreed. The implementation
   plan lives **on the ticket** (`## Implementation plan`), never in
   Requirements and never in a `plans/` folder.

Before proposing architecture, writing Requirements, creating tickets,
writing a plan, executing the board, or writing code, load `bora-plan`,
`bora-tdd`, or `bora-execute` when they match. After a project-level
"go", load `bora-execute` and walk remaining tickets. Never ask
"should I continue?" between tickets. Show completed vs remaining after
each ticket.

The human runs `bora dev` for setup (`init`, `skill install`, `upgrade`)
and conversational approval. You run ticket, plan, status, and lint
commands. Do not ask the human to type those.

## Briefing sequence

When you join a session with no prior context, read in this order:

1. AGENTS.md (root — this file)
2. The human-referenced project briefing:
   `docs/ai/<path>/(YYYY-MM-DD) {ProjectName}.md`
3. Discuss architecture with the human before writing Requirements.
   Do not skip this conversation. Do not fill in the Requirements
   file from Project.md alone.
4. After agreement, author/update:
   `docs/ai/<path>/(YYYY-MM-DD) {ProjectName} Requirements.md`
5. `docs/ai/<path>/Status.md`  (read only — never hand-edit)
6. When implementing: create tickets from the Requirements
   Tasks Breakdown. After the human says go, load `bora-execute` and
   work through the board. Write `## Implementation plan` on each
   ticket (`bora-plan`) before code. Use `bora-tdd` per plan task.
7. `docs/ai/<path>/tickets/<id>.md` as the active work demands
8. If budget-constrained, run `bora dev context <path> --budget N`

Hard gates: no tickets until Requirements are approved; no production
code until the current ticket has an implementation plan; no `done`
without Commit criteria. Commit message:
`{ticket-id} {task-id}: {title}`.

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

Example (`bora dev init "QromaCore/Hamburg/Gallery Refactor"` on 2026-08-14):

```
docs/
  ai/
    QromaCore/
      Hamburg/
        Gallery Refactor/
          (2026-08-14) Gallery Refactor.md
          (2026-08-14) Gallery Refactor Requirements.md
          Status.md
          tickets/
            .gitkeep
```

## Workflows

### Orient, then Requirements, then tickets

1. Read the referenced project briefing and confirm scope with the human.
2. Discuss architecture: components, data model, key flows, constraints,
   non-goals. Propose options; wait for agreement.
3. Write or update `(YYYY-MM-DD) {ProjectName} Requirements.md`:
   architecture, requirements, acceptance criteria, testing
   requirements, commit criteria, Tasks Breakdown, risks, and open
   questions. Bump `last_reviewed`.
4. Only then create tickets from the Tasks Breakdown:
   `bora dev ticket new <project_path> "<title>"`.
   `<project_path>` is the same value passed to `bora dev init`.
   Use `--parent` when a breakdown item splits.
5. Tickets may be assigned in conversation to one or more agents; each
   agent still stays inside this project directory and updates only the
   tickets it is working.
6. After ticket changes, run `bora dev status <project_path>` so
   `Status.md` reflects current work.
7. Before marking a ticket or subtask `done`, and before any git
   commit, satisfy **Commit criteria** in the Requirements file: the
   subtask's completion tests pass, the change meets the requirement,
   and build/tests pass (including platform builds such as macOS/iOS
   when that is the target). Commit message format:
   `{ticket-id} {task-id}: {title}`.

### After Requirements are approved ("go")

1. Create tickets from the Tasks Breakdown if they do not exist.
2. Load `bora-execute`. Do not stop after the first ticket.
3. For each unblocked ticket: write `## Implementation plan` if missing,
   then `bora-tdd` (failing test → implement → verify → commit one
   plan task). Check tasks off with `bora dev plan task`.
4. After each ticket `done`, show completed vs remaining (`bora dev
   status`) and start the next ticket. Never ask whether to continue.
5. Stop only when the board is complete, blocked with no other
   runnable work, verification failed twice, or the human interrupted.

### Resuming work on an existing ticket

1. Run `bora dev ticket show <project_path> <id>` (or read the file
   directly). Example:
   `bora dev ticket show QromaCore/Hamburg/Gallery\\ Refactor 20260811-01`
2. Check the latest entry in the body Notes section.
3. Check subtask checkboxes for what's already done.
4. If status is `todo`, set it to `in-progress`:
   `bora dev ticket set <project_path> <id> status in-progress`.
5. Append a dated Notes entry when you make meaningful progress:
   `bora dev ticket note <project_path> <id> "<text>"`.
6. After ticket changes, run `bora dev status <project_path>`.
   Example: `bora dev status QromaCore/Hamburg/Gallery\\ Refactor`.

### Marking a ticket complete

1. Before `bora dev ticket set <project_path> <id> status done` (or
   setting a subtask to `done`), run the Commit criteria checks in the
   Requirements file: completion tests pass, the change meets the
   requirement, and build/tests pass.
2. Verify all acceptance criteria are met and all body checkboxes are
   checked.
3. Then set status: `bora dev ticket set <project_path> <id> status done`.
   The `closed` date populates automatically.
4. If the human wants a commit, use message
   `{ticket-id} {task-id}: {title}`. Do not commit if build or
   completion tests failed.

### Recording an architectural decision

There is no decision command. After agreeing with the human, edit the
project's Requirements file directly (typically under Architecture or
Open questions).

## Validation

After any write to a ticket file, run `bora dev lint <project_path>`,
then `bora dev status <project_path>`. Don't trust your own YAML output
without verification — lint catches frontmatter errors before they
corrupt project state.

## Frontmatter reference

Tickets live at `docs/ai/<path>/tickets/<id>.md`. Ticket IDs are unique
per-project, not repo-global.

Ticket frontmatter fields:

- `id` — `YYYYMMDD-NN-slug` format. Set by
  `bora dev ticket new <project_path> "<title>"`; don't change.
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


def render_agents_md() -> str:
    start_tag = f'<!-- bora-managed:start version="{AGENTS_TEMPLATE_VERSION}" -->'
    return (
        "# Agent Instructions\n\n"
        f"{start_tag}\n"
        f"{AGENTS_MD_BODY.strip()}\n"
        f"{MANAGED_END}\n\n"
        "## Project-specific instructions\n\n"
        "Add local rules below this heading. `bora dev upgrade` never overwrites\n"
        "this section.\n"
    )


def replace_managed_region(text: str, *, version: str = AGENTS_TEMPLATE_VERSION) -> str:
    """Replace the managed block; preserve everything after the end marker."""
    start_m = MANAGED_START_RE.search(text)
    end_m = MANAGED_END_RE.search(text)
    if not start_m or not end_m or end_m.start() < start_m.end():
        return render_agents_md()
    start_tag = f'<!-- bora-managed:start version="{version}" -->'
    new_block = f"{start_tag}\n{AGENTS_MD_BODY.strip()}\n{MANAGED_END}"
    return text[: start_m.start()] + new_block + text[end_m.end() :]


AGENTS_MD = render_agents_md()



PROJECT_MD_TEMPLATE = """---
last_reviewed: {today}
focus: "Initial setup. Replace this with the current milestone."
---

# Project

## Background

What is this project? Why does it exist? What's the context a stranger
would need to understand the rest of this document?

## Goals

What are we trying to accomplish? List the top-level outcomes.

- Goal 1
- Goal 2

## Non-goals

What are we explicitly *not* doing? Naming this saves arguments later.

- Non-goal 1

## Target users

Who is this for? What do they need? What do they already know?

## User stories

The concrete scenarios this product supports.

- As a [user type], I want to [action], so that [outcome].
- As a [user type], I want to [action], so that [outcome].

## Constraints

Technical, business, or practical constraints that shape the design.

- Constraint 1
- Constraint 2

## Success criteria

How will we know this project is done — or at least working?

- Criterion 1
"""


def _normalize_project_frontmatter_dump(dumped: str) -> str:
    """Adjust PyYAML quoting so scaffold output matches project conventions."""
    dumped = re.sub(
        r"last_reviewed: '(\d{4}-\d{2}-\d{2})'",
        r"last_reviewed: \1",
        dumped,
    )
    return dumped.replace("focus: ''", 'focus: ""')


def render_project_frontmatter(hierarchy, tags, today):
    data = {}
    if tags:
        for label, segment in zip(tags, hierarchy):
            data[tag_key(label)] = segment
        data["tags"] = list(tags)
    data["hierarchy"] = list(hierarchy)
    data["last_reviewed"] = today
    data["focus"] = ""
    dumped = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).rstrip()
    dumped = _normalize_project_frontmatter_dump(dumped)
    return f"---\n{dumped}\n---\n"


def render_project_md(hierarchy, tags, today):
    body = """
# Project

## Background

What is this project? Why does it exist? What's the context a stranger
would need to understand the rest of this document?

## Goals

What are we trying to accomplish? List the top-level outcomes.

- Goal 1
- Goal 2

## Non-goals

What are we explicitly *not* doing? Naming this saves arguments later.

- Non-goal 1

## Target users

Who is this for? What do they need? What do they already know?

## User stories

The concrete scenarios this product supports.

- As a [user type], I want to [action], so that [outcome].

## Constraints

Technical, business, or practical constraints that shape the design.

- Constraint 1

## Success criteria

How will we know this project is done — or at least working?

- Criterion 1
"""
    return render_project_frontmatter(hierarchy, tags, today) + body


REQUIREMENTS_MD_TEMPLATE = """---
last_reviewed: {today}
hierarchy: []
---

# {project_name} Requirements

Placeholder. Discuss architecture with the human, then fill every section.

## Overview

## Goals

## Non-goals

## Architecture

### Components

### Data model

### Key flows

## Requirements

Functional and non-functional requirements.

## Acceptance criteria

## Testing requirements

Name the project verify command(s) here (for example `xcodebuild` for an
iOS/macOS target; otherwise that project's equivalent). Ticket plan
**Verify:** lines copy from this section — do not invent a generic
`npm test` on a native Apple project.

## Commit criteria

Before marking a ticket or subtask done, and before any git commit:

- [ ] Plan-task verification command passed (RED then GREEN)
- [ ] The change meets the matching requirement and acceptance criteria
- [ ] Build tests passed (for example `xcodebuild` on macOS/iOS; otherwise the project's equivalent tests)
- Commit message format: `{{ticket-id}} {{task-id}}: {{title}}`

## Tasks Breakdown

Work items that become tickets. Do not create tickets until this section is agreed.
Each item becomes a ticket. The implementation plan is written on the ticket
when execute reaches it — not in this file.

## Risks and assumptions

## Open questions
"""


WRITER_AGENTS_MD = """# Bora Writer Agent Instructions

## Role & Boundaries

You are a research and context assistant. You NEVER write manuscript content.
You assist with storyline analysis, research logging, pacing feedback, and
context briefing.

## Workflow Rules

- Record all research and agent interactions in the relevant chapter's
  `Research.md` under topic sections
- Use YAML frontmatter per topic section (see Research.md spec)
- When prompted with `bora write status`, compile context and output a
  structured summary prompt
- Respect author frontmatter statuses: `draft`, `in-progress`, `completed`
- Never modify `.md` manuscript files directly

## Summary Generation

- Read `doc/ai/Project.md`, `Chapters/*/ChapterProject.md`,
  `Chapters/*/Research.md`
- Output YAML frontmatter + body summary to stdout
- Author reviews and saves the output as `Summary.md`
"""

WRITER_PROJECT_MD = """---
profile: write
status: outline
last_updated: ""
---

# Project Overview

> [Premise, logline, target audience, genre]

## Plot Breakdown

### Act I

### Act II

### Act III

## Character Bibles

- [Character Name]: role, arc, voice notes

## Worldbuilding Rules

- Magic/tech limits, geography, society norms

## Timeline & Pacing

- Chronology of events, intended rhythm per chapter

## Major Creative Decisions

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
"""

WRITER_SUMMARY_MD = """---
profile: write
last_generated: ""
total_words: 0
chapters_completed: 0
chapters_in_progress: 0
status: active
---

# Story Synopsis

[Chapter-by-chapter summary + research integration notes]

## Context State

- Active arcs, unresolved research, pacing notes
- Next chapter focus
"""


OBSIDIAN_SKILL_MD = """# Bora Writer — Obsidian Vault Agent Instructions

## Role & Boundaries

You are a research and context assistant operating inside an Obsidian vault
that uses the bora writer profile. You NEVER write manuscript content.

## Vault Structure

- `Chapters/Chapter NNN - Name/` — one directory per chapter
  - `NNN - Name.md` — manuscript (read-only for agents)
  - `NNN - ChapterProject.md` — planning & status frontmatter
  - `NNN - Research.md` — research interaction log
- `doc/ai/Project.md` — story overview, plot, characters, worldbuilding
- `Summary.md` — latest compiled context (generated by `bora write status`)
- `Summary/` — archive of previous summaries

## Workflow Rules

- Record research interactions in the relevant `Research.md` under topic sections
- Never modify `.md` manuscript files
- When prompted for a status summary, read Project.md + all ChapterProject.md +
  all Research.md, then synthesise to stdout for the author to save as Summary.md
"""

OBSIDIAN_MANIFEST_JSON = """{
  "id": "bora-writer",
  "name": "Bora Writer",
  "version": "0.3.0",
  "minAppVersion": "1.4.0",
  "description": "Research and context assistant for bora write-profile projects.",
  "author": "Bora"
}
"""

OBSIDIAN_README_MD = """# Bora Writer Plugin

This directory was created by `bora write skill install obsidian`.

## Setup

1. Enable community plugins in Obsidian (Settings → Community plugins → Turn off Safe mode).
2. This plugin does not ship executable JavaScript. The `SKILL.md` file is a
   prompt template — paste its contents into your AI assistant's system prompt
   or context window to orient it to your vault's bora writer structure.

## Uninstall

Run `bora write skill uninstall obsidian` from your project root to remove this directory.
"""


WRITER_CHAPTER_PROJECT_MD = """---
chapter: {padded}
status: draft
target_words: 0
---

# Chapter {padded} - {name}

## Plot Goals

- Setup/Inciting/Reversal/Climax beats

## Character Arcs

- POVs, emotional states, revelations

## Pacing & Tone

- Rhythm, atmosphere, key scenes

## Notes for Agent

- Research topics, questions to explore
"""

WRITER_RESEARCH_MD = """# Chapter {padded} Research Log

## Topic: [Concise Title]

---
topic: "Topic Title"
date: ""
agent: ""
word_count: 0
verified: false
---

[Author prompt/question here...]

[AI response + reasoning here...]
[Key quotes, sources, or structural notes...]
"""


def ticket_template(
    ticket_id: str,
    title: str,
    ticket_type: str,
    priority: str,
    parent: str = "",
    today: str = "",
) -> str:
    """Render a new ticket file as a string.

    We use a hand-built string rather than yaml.safe_dump for the initial
    scaffolding because we want the empty fields to be visible and ordered
    consistently — yaml.safe_dump would either omit them or alphabetize them.
    """
    today = today or date.today().isoformat()
    parent_line = f'parent: "{parent}"' if parent else "parent:"
    return f"""---
id: {ticket_id}
title: "{title}"
type: {ticket_type}
priority: {priority}
status: todo
created: {today}
updated: {today}
closed:
notes: ""
{parent_line}
depends_on: []
subtasks: []
---

## Description

What is this ticket and why does it exist?

## Acceptance criteria

- [ ] Concrete, checkable condition
- [ ] Another concrete condition

## Context

Links to relevant code, prior tickets, decisions in the project's
Requirements file, or anything else a model working on this would need
to know.

## Subtasks

Detailed checklist. Major subtasks should also appear in the frontmatter
`subtasks` field so they show up in `Status.md`.

## Implementation plan

Status: draft
Current task:

## Notes

Append-only running log. Each entry dated.
"""
