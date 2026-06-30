# Agent Instructions

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
