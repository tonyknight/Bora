"""Static templates for scaffolded files.

Kept in a single module rather than separate files because they're tightly
coupled to the framework's conventions and shipping them as package data
just adds setup complexity. If they grow large, split them out.
"""

from __future__ import annotations

from datetime import date


AGENTS_MD = """# Agent Instructions

## Philosophy

This project uses a structured collaboration framework. Documentation in
`docs/ai/` is your shared workspace with the human. You read it to get
oriented, you propose updates to it as work progresses, and you treat it
as the source of truth about project state.

Three principles:

1. **`Tasks.md` is auto-generated.** Never edit it directly. Update tickets
   instead, then run `bora status` to regenerate.
2. **`Project.md` and `Architecture.md` are collaborative.** Propose changes
   in conversation; don't edit silently.
3. **Tickets are where work happens.** Update their status, notes, and
   subtasks as you progress.

## Briefing sequence

When you join a session with no prior context, read in this order:

1. This file (`AGENTS.md`)
2. `docs/ai/Project.md` — what we're building and why
3. `docs/ai/Architecture.md` — how we've decided to build it
4. `docs/ai/Tasks.md` — current state of work
5. Specific files in `docs/ai/tickets/` as the active work demands

If your context budget is tight, run `bora context --budget <tokens>`
to get a token-bounded briefing.

## Workflows

### Starting a new feature

1. Read `Project.md` and `Architecture.md` to confirm scope.
2. Propose an implementation plan in conversation with the human.
3. Once agreed, create one or more tickets via `bora ticket new`.
4. If the feature decomposes, use `--parent` to link child tickets.
5. Populate each ticket's Description, Acceptance criteria, Context, and
   Subtasks (frontmatter for major subtasks; body checkboxes for small ones).

### Resuming work on an existing ticket

1. Run `bora ticket show <id>` (or read the file directly).
2. Check the latest entry in the body Notes section.
3. Check subtask checkboxes for what's already done.
4. If status is `todo`, set it to `in-progress`:
   `bora ticket set <id> status in-progress`.
5. Append a dated Notes entry when you make meaningful progress.

### Marking a ticket complete

1. Verify all acceptance criteria are met.
2. Verify all body checkboxes are checked.
3. Run `bora ticket set <id> status done`.
4. The `closed` date populates automatically.

### Proposing changes to `Project.md` or `Architecture.md`

1. State the change you want to make and why.
2. Wait for human confirmation.
3. Update the file, including bumping its `last_reviewed` date in the
   frontmatter.
4. If the change invalidates open tickets, flag this explicitly and
   propose what to do (close, revise, or split).

### Recording an architectural decision

1. Append a dated entry to the "Decision log" section at the bottom of
   `Architecture.md`. Or run `bora decision new "<title>"` to scaffold one.
2. Include: what was decided, alternatives considered, and reasoning.

## Validation

After any write to a ticket file, run `bora lint`. Don't trust your own
YAML output without verification — it catches frontmatter errors before
they corrupt project state.

## Frontmatter reference

Ticket frontmatter fields:

- `id` — `YYYYMMDD-NN-slug` format. Set by `bora ticket new`; don't change.
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


ARCHITECTURE_MD_TEMPLATE = """---
last_reviewed: {today}
---

# Architecture

## Overview

One or two paragraphs describing the shape of the system at a high level.
What are the main pieces? How do they fit together?

## Components

Break the system into its parts. For each, describe what it does and how
it relates to the others.

### Component A

What it does. Key interfaces or boundaries.

### Component B

What it does. Key interfaces or boundaries.

## Data model

Key entities, their relationships, and how state is persisted.

## Key flows

Walk through the most important user-facing or system-level interactions.

### Flow 1: [name]

1. Step
2. Step

## Open questions

Things we haven't decided yet. Each entry should have enough context that
a model joining mid-project understands what's at stake.

- Question 1
- Question 2

## Decision log

Append-only record of architectural decisions. Each entry is dated.
Include: what was decided, alternatives considered, and reasoning.

### {today} — Initial scaffolding

Decided to use the bora framework for project documentation and ticketing.
Alternatives considered: ad-hoc Markdown notes, Notion, Linear. Chose bora
because it lives in the repo, is editable by AI agents, and is designed
for context portability across model sessions.
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

Links to relevant code, prior tickets, decisions in `Architecture.md`,
or anything else a model working on this would need to know.

## Subtasks

Detailed checklist. Major subtasks should also appear in the frontmatter
`subtasks` field so they show up in `Tasks.md`.

## Notes

Append-only running log. Each entry dated.
"""
