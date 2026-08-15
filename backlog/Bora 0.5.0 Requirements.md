# Bora 0.5.0 Requirements

## Overview

Bora 0.4.5 already orients an agent: hierarchical projects, a dated briefing, a dated Requirements file, tickets, and `Status.md`. What it does not do is tell the agent **how to turn an approved project into git history without stalling after each ticket**.

0.5.0 folds in a thin slice of Superpowers-style discipline — per-ticket implementation plans, test-first work, one commit per plan task, and a project-level execute loop — **without** becoming Superpowers and **without** asking the human to drive a new command surface.

The product bet:

> Bora remains the project-driven system of record. Skills tell the agent when to plan, when to wait for approval, and how to execute **the whole ticket board**. The CLI is a small, git-friendly file API the **agent** calls. The human mostly talks, reviews Markdown, and says yes once.

This document supersedes both the earlier execute-engine sketch and the `plans/` folder draft. Skills deferred from this slice (`bora-design`, `bora-worktree`, `bora-review`, `bora-debug`, `bora-verify`, `bora-finish`, optional subagent execute, Cursor install) live in `backlog/Bora 0.5.5 Requirements.md`.

---

## 1. Design principles

1. **Project-driven, not session-driven.** Briefing, Requirements, tickets, and `Status.md` live under `docs/ai/<path>/` and travel with the repo. A new chat resumes from those files.
2. **Human-light CLI.** The human runs setup plus conversational approval of Requirements (and a single “go”). After that, the agent runs almost every `bora dev` command and walks remaining tickets without asking permission between them.
3. **Thin CLI, thick skill.** The CLI scaffolds, validates, and updates structured files. It does not generate plans, dispatch subagents, or run TDD. Skills encode the methodology and name the CLI calls.
4. **Skills must trigger correctly.** Each skill's `description` is a trigger contract ("Use when…"), not a workflow summary. The bootstrap skill forces a skill check before acting. Wrong triggers are a product bug.
5. **Git-native work.** A plan task is the unit that becomes a commit. Task IDs appear in commit messages so `git log` is the execution ledger. Progress is Markdown checkboxes on the ticket, not a side folder and not YAML blobs.
6. **No extra document types.** 0.5.0 does **not** add `plans/`. Requirements stays the spec. The implementation plan lives **inside the ticket**.
7. **Ship a useful slice, then deepen it.** 0.5.0 includes plan + TDD + execute-the-board. Worktrees, design-skill, review, debug, verify-as-skill, finish/merge, and subagent execute wait for 0.5.5 after this loop has been used on real projects.
8. **Dev profile only.** The `write` profile is untouched.
9. **Backward compatible.** Tickets without an implementation-plan section remain valid. Existing command signatures stay.
10. **Skills are the product.** `bora dev skill install` is what makes 0.5.0 real. Without the pack, the files exist but the gates (no code before Requirements, execute the whole board, TDD, commit contract) will not fire reliably.

---

## 2. Three documents (not a `plans/` folder)

A first-time engineer will call several of these “the plan.” They are not the same file.

| What they are thinking | File | Who writes it | 0.5.0 role |
|---|---|---|---|
| What are we building, and why? | Dated **project briefing** `(YYYY-MM-DD) {ProjectName}.md` | Human, agent may help | Unchanged from 0.4.5. Session entry point. |
| How should it be designed? What is done? | Dated **Requirements** `(YYYY-MM-DD) {ProjectName} Requirements.md` | Agent drafts after architecture conversation; human approves | Project spec. Tasks Breakdown **becomes tickets**. Not a commit script. |
| What commits will this ticket produce? | `## Implementation plan` **on the ticket** | Agent, when execute reaches that ticket | 0.5.0. `T01`…`Tn`, files, verify command, commit line. |

**Requirements vs the implementation plan.** Merging them would make both worse. Requirements should stay stable after approval. The implementation plan changes every commit (checkboxes, `current_task`). If that lived in Requirements, every ticket would dirty the spec, `bora dev context` would balloon, and two tickets could not progress without merge conflicts in one file. Requirements answers *what does done mean for the project?* The ticket plan answers *what commits does this ticket produce?*

**Why not `plans/`?** That was an over-reaction to “don’t put a huge YAML plan in frontmatter.” Tickets are already the git-friendly work item. One ticket file holds description, acceptance criteria, the `T01`…`Tn` plan, and notes. No third tree. No `docs/superpowers/plans/`.

**Project-wide verify commands** (for example `xcodebuild -scheme ShareExtension`) belong in Requirements **Testing requirements** / **Commit criteria**. Ticket plan **Verify:** lines copy from there; they do not invent `npm test` on an iOS/macOS repo.

---

## 3. What 0.5.0 is (and is not)

### In scope

- Per-ticket **implementation plan** as a Markdown section on the ticket (not a `plans/` folder, not YAML in frontmatter, not a chapter of Requirements).
- Optional ticket frontmatter `plan_status` and `current_task` so `Status.md` can show progress.
- A **skill pack**: `bora`, `bora-plan`, `bora-tdd`, **`bora-execute`**.
- After Requirements approval and one “go”, the agent **creates tickets from the Tasks Breakdown and works through the board** until it is done, blocked, or interrupted.
- Between ticket completions, show **completed vs remaining** (from `Status.md` / ticket list). Do not ask “continue to the next ticket?”
- Lint + `Status.md` awareness of plan progress on the ticket.
- Commit-message contract `{ticket-id} {task-id}: {title}`.
- README / `AGENTS.md` / skill-template updates.

### Out of scope (see 0.5.5)

- A Python `bora dev execute` orchestrator that shells out to coding agents. Execute is a **skill** (this remains true in 0.5.5).
- Git worktree creation/cleanup (`bora-worktree`).
- Superpowers-style design/brainstorm skill that authors Requirements in sections (`bora-design`).
- Subagent-driven development and per-task or per-ticket code-review dispatch (`bora-review`, optional subagent execute).
- Systematic debugging skill (`bora-debug`) and a standalone verification skill (`bora-verify`).
- `finishing-a-development-branch` merge/PR menu (`bora-finish`). Human still ships the branch in 0.5.0.
- Framework detection (jest/vitest/pytest/xcodebuild). The **plan task** names the verification command, copied from Requirements.
- Coverage gates.
- `docs/ai/logs/`.
- Loading or vendoring Superpowers skills by name. Bora owns its skills; they *encode* Superpowers patterns.
- A new ticket status `planned`. Keep `todo | in-progress | blocked | done`.
- Write-profile changes.
- Migration of pre-0.4.5 flat `docs/ai/` trees.
- Cursor as an install target (open in 0.5.0; planned in 0.5.5).

---

## 4. Operator model

### 4.0 First-time workflow (existing iOS/macOS codebase)

This is the happy path a mid-level engineer should be able to follow from README + `AGENTS.md`. Example: add a Share Extension target to an existing photo app.

**Once on the machine**

```bash
pipx install bora
bora dev skill install all          # or claude / opencode
```

Skill install is required. Without it they have Markdown; they do not have `bora-plan` / `bora-tdd` / `bora-execute`.

**Once per new Bora project** (the only project command they must type):

```bash
cd ~/src/PhotoApp
bora dev init "PhotoApp/iOS/Share Extension" --tags Codebase,Target,Project
```

That scaffolds:

```
AGENTS.md                                          ← only if missing
docs/ai/PhotoApp/iOS/Share Extension/
  (YYYY-MM-DD) Share Extension.md                  ← they write what/why here
  (YYYY-MM-DD) Share Extension Requirements.md     ← placeholder until conversation
  Status.md
  tickets/
```

**Where they write the project thinking:** the dated briefing, not Requirements, not a ticket.

**How they get Requirements:** they start an agent session and point at that briefing. They do **not** run a plan command. Example prompt:

> Work in `docs/ai/PhotoApp/iOS/Share Extension/(YYYY-MM-DD) Share Extension.md`. Discuss architecture with me before filling Requirements. Do not create tickets yet.

The `bora` skill must stop the agent from skipping to code. After they say the design is right, the agent fills Requirements (including Testing requirements / Commit criteria, e.g. `xcodebuild` for the new target). They review it like a PR and say **approved**.

**How they execute:** they say **go**. The agent creates tickets from the Tasks Breakdown, loads `bora-execute`, and walks the board. After each ticket it shows done vs remaining. They watch commits of the form `{ticket-id} T01: …`. Merge/PR is still their git. They should not need another `bora dev` command until they want a PR.

Chat-only models (no shell): `bora dev context "PhotoApp/iOS/Share Extension"` and paste. Execute quality is weaker.

### 4.1 What the human does

Typical session after bora is installed:

1. Point the agent at the project briefing (`docs/ai/<path>/(YYYY-MM-DD) {ProjectName}.md`).
2. Discuss architecture; **approve** the Requirements file in conversation (and/or by reading the diff).
3. Say **go** (implement the Tasks Breakdown / the tickets). That is the project-level execution gate — not a per-ticket prompt.
4. Watch the agent report, after each ticket, what is done vs what is left. Interrupt in language if something is wrong.
5. Decide how to integrate the branch (human git / PR). 0.5.0 does not automate this.

Setup, once per machine or repo:

- `bora dev init <project_path> …` when starting a new project.
- `bora dev skill install <tool>` (or `all`) so the skill pack is discoverable.

Optional, for chat-only models with no shell:

- `bora dev context <project_path>` — paste briefing. Execute quality will be weaker without CLI + skills.

The human does **not** need to type `ticket`, `plan`, `lint`, or `status` on the happy path. Those are agent API.

### 4.2 What the agent does

After Requirements are approved and the human says go:

1. Create tickets from the Tasks Breakdown (`bora dev ticket new`) if they do not already exist.
2. Load **`bora-execute`**. Do not stop after the first ticket.
3. For each next unblocked ticket (see §5.4):
   - If it has no implementation plan, load `bora-plan` and write `## Implementation plan` on that ticket.
   - Set ticket `in-progress`, load `bora-tdd`.
   - For each plan task: failing test → implement → verify using the task's command → commit with the contract in §7 → check the task off → `bora dev plan task` / note / status.
   - When the last task is done: verify acceptance criteria, set ticket `done`.
   - **Show completed vs remaining** (§5.5). Then start the next ticket. Do not ask whether to continue.
4. Stop only on: board complete, `blocked` with no other unblocked work, repeated verification failure, genuine ambiguity, or human interrupt.

If `bora` is missing from `PATH`, the agent edits the same files by hand and still follows the skills. Lint remains the check that YAML was not corrupted.

### 4.3 Command ownership

| Command | Who runs it in the happy path |
|---|---|
| `bora dev init` | Human |
| `bora dev upgrade` | Human (after installing a new bora CLI; once per repo) |
| `bora dev skill install / list / uninstall` | Human (setup). `upgrade` also refreshes an existing pack. |
| `bora dev context` | Human, chat-only only |
| `bora dev ticket *` | Agent |
| `bora dev plan *` | Agent |
| `bora dev status` | Agent (after each ticket, and after mutations) |
| `bora dev lint` | Agent, after any ticket write |
| git commit | Agent, once per completed plan task |

There is no human-facing `bora dev execute` command. “Go” in chat is what starts `bora-execute`.

### 4.4 Existing Bora projects (upgrade)

`bora pipx upgrade` / a new CLI on `PATH` does **not** by itself change files in the repo. Today (0.4.5) `bora dev init` writes `AGENTS.md` only when it is missing; `--force` overwrites it **and** project scaffold files. That is not an upgrade path.

0.5.0 adds **`bora dev upgrade`**: the human command that brings an already-initialized repo in line with the CLI they just installed.

After `pipx upgrade bora` (or equivalent), in the repo:

```bash
bora dev upgrade
```

That command, and only that command, is how `AGENTS.md` (and the installed skill pack) catch up to 0.5.0. See §9.7. Do not tell people to `init --force`.

---

## 5. Skill pack and trigger matrix

This is the load-bearing design of 0.5.0. If skills do not fire at the right moment, the CLI is unused and the methodology does not happen.

### 5.1 Install shape

`bora dev skill install` installs a **pack**, not a single `SKILL.md`:

```
<tool-skills-root>/
  bora/SKILL.md
  bora-plan/SKILL.md
  bora-tdd/SKILL.md
  bora-execute/SKILL.md
```

Uninstall removes only directories whose `SKILL.md` declares a bora-owned `name:` (`bora`, `bora-plan`, `bora-tdd`, `bora-execute`). Existing install paths for `claude` and `opencode` stay; adding Cursor as an install target is desirable if it is a small extension of the current registry, not a blocker.

The pack is also what `bora dev skill install --project` writes into the repo.

### 5.2 Description rules (trigger-only)

Follow Superpowers' skill-discovery rule:

- `description` starts with `Use when…`
- It names **situations**, not the procedure
- It does **not** summarize TDD, commit format, ticket ordering, or CLI steps
- Keep it well under 500 characters

### 5.3 Skills shipping in 0.5.0

#### `bora` — bootstrap / orientation

**Trigger (`description` intent):** Use when the repo has an `AGENTS.md` referring to bora, a `docs/ai/<path>/` project (dated briefing, Requirements, `Status.md`, or `tickets/`), or when the user points at a project briefing. Use at the start of a session in a bora project before reading or editing those files.

**Body must include:**

- Existing briefing sequence and scope guardrail (0.4.5).
- **Skill check:** before proposing architecture, writing Requirements, creating tickets, writing a plan, executing the board, or writing code, consider `bora-plan`, `bora-tdd`, and `bora-execute` and load the one that matches.
- Hard gates: no tickets until Requirements are approved; no production code until the current ticket has an implementation plan; no `done` without Commit criteria.
- Human-light rule: the agent runs the CLI; do not ask the human to type `bora dev` commands unless setup is missing.
- After a project-level “go”, load `bora-execute`. Do not wait for a per-ticket “please do the next one.”
- Implementation plans live in the ticket (`## Implementation plan`), never in Requirements, never under `plans/` or `docs/superpowers/`.

#### `bora-plan` — implementation plans

**Trigger (`description` intent):** Use when a ticket in a bora project needs an implementation plan before code (Requirements already approved); when the user asks to plan a ticket; or when `bora-execute` has selected a ticket that has no `## Implementation plan` yet. Do not use for architecture discussion (that is Requirements) or while a ticket with an existing plan is already being implemented.

**Body must include:**

- Write `## Implementation plan` on **that ticket** (template in §6). Do not create a `plans/` file. Do not append the commit script to Requirements.
- Task right-sizing: each task is one commit, independently verifiable, with exact files and a verification command taken from the project's testing/commit criteria (or named by the agent if Requirements already states it).
- No placeholders (`TBD`, "add tests later", "similar to task N").
- During **`bora-execute`**, do **not** stop for per-ticket plan approval. The project-level “go” already covers it. Stop only if the ticket cannot be planned without a design decision that belongs in Requirements.
- If the human is explicitly planning a single ticket *before* saying go, wait for their yes on that ticket, then stop (they have not started execute).
- Resume: if the section exists and `plan_status` is `draft`, continue editing it.

#### `bora-tdd` — test-first implementation of a plan task

**Trigger (`description` intent):** Use when implementing a feature, bugfix, or plan task in a bora project; before writing production code; or before marking a plan task or ticket `done`.

**Body must include:**

- Iron law: no production code without a failing test first (Superpowers TDD, adapted).
- Exceptions — ask the human: `spike` tickets, generated code, pure config/docs. Default is TDD.
- Cycle: RED (write test, run it, confirm the failure is the right one) → GREEN (minimal code, run the **task's** verification command) → commit (§7) → next task.
- Do not invent a generic `npm test` if the plan task names `pytest` or `xcodebuild`. The ticket plan is the source of the command.
- Do not mark a task complete on a pass you did not just run.
- After each task: update plan checkboxes / `current_task`, `bora dev lint`, ticket note if something non-obvious happened.
- After the **ticket** is complete, return to `bora-execute` (do not open a “what next?” question).

#### `bora-execute` — walk the ticket board

**Trigger (`description` intent):** Use when a bora project's Requirements are approved and the user asks to implement, execute, go, or work through the tickets; when resuming a project that still has `todo` / `in-progress` / unblocked tickets; or after a ticket is marked `done` and other tickets remain. Do not use before Requirements approval, and do not use for a single isolated “just this one file” request that is not project execution.

**Body must include:**

- This is Superpowers' executing-plans analogue, **at ticket granularity**, over Bora's board — not a Python daemon.
- Create missing tickets from the Requirements Tasks Breakdown, then loop.
- **Ticket order:** skip `done`; skip `blocked` unless the human unblocked it; honor `depends_on` (all listed tickets must be `done`); then highest priority (`high` > `medium` > `low`); then oldest `id`. One ticket `in-progress` at a time unless the human named a parallel split.
- For the selected ticket: `bora-plan` if needed, then `bora-tdd` until that ticket is `done` or `blocked`.
- **Between tickets (required):** run `bora dev status <project_path>` and **show the human** a completed-vs-remaining list (§5.5). Then immediately start the next unblocked `todo`. Never ask “should I continue?”
- **Stop** (and say why) when: no unblocked work remains; a ticket is `blocked` and nothing else is runnable; verification failed twice on the same task; the plan collides with Requirements; or the human interrupted.
- Resume: read `Status.md`, the in-progress ticket's `current_task`, and `git log --grep=<ticket-id>`. Continue the in-progress ticket first, then the rest of the board.
- Do not create worktrees (deferred). Do not present merge/PR options (deferred `bora-finish`).

### 5.4 Ticket pick order (execute)

Pseudocode the skill and any helper CLI must follow:

```
runnable = tickets where status not in (done, blocked)
            and every depends_on id has status done
sort runnable by (priority_rank, id)
if any status == in-progress: work that one first
else: take runnable[0]
```

If `runnable` is empty and some tickets are `blocked`, report the blocked set and stop. If all are `done`, report the board complete and stop.

### 5.5 Completed vs remaining (between tickets)

After each ticket reaches `done` (and also when execute starts or resumes), the agent must show a short list, not only regenerate a file the human might not open.

Required shape (example):

```
Share Extension — 2 done · 1 in-progress · 4 remaining

Done
- 20260814-01-add-target — Add Share Extension target
- 20260814-02-app-group — Shared App Group entitlements

Now
- 20260814-03-import-pipeline — Import into app library  [T02/T05]

Remaining
- 20260814-04-share-ui — Share sheet UI
- 20260814-05-tests — Target test host
- 20260814-06-signing — Capabilities and signing
- 20260814-07-docs — README and scheme docs

Blocked
- (none)
```

Source of truth is ticket state after `bora dev status`. Counts must match `Status.md`. Then continue. This display is how 0.5.0 avoids feeling like “ticket-by-ticket mode” without hiding progress.

### 5.6 Trigger matrix (acceptance for the pack)

| Situation | Must load | Must not skip |
|---|---|---|
| New session, human names a project briefing | `bora` | Jumping into code |
| Architecture not yet agreed | `bora` | `bora-plan`, `bora-tdd`, `bora-execute` |
| Requirements approved, “let’s implement” / “go” | `bora` then `bora-execute` | Doing only the first ticket, then asking to continue |
| Execute selected a ticket with no plan section | `bora-plan` then `bora-tdd` | Writing code with no `T01…`; writing the plan into Requirements |
| Implementing task T03 | `bora-tdd` | Several tasks in one commit |
| Ticket just marked `done`, others remain | `bora-execute` (show board, next ticket) | Ending the session; “want me to do the next ticket?” |
| “Mark it done” / “commit this” | `bora-tdd` (verify first) | Status flip without evidence |
| Resume, ticket `in-progress` | `bora`, `bora-execute`, `bora-tdd` at `current_task` | Restarting the ticket or the board |
| Chat-only paste of `bora dev context` | `bora` if the model has skills; else `AGENTS.md` in the paste | Inventing a `plans/` folder |

`AGENTS.md` restates the same gates so models **without** a skill loader still see them.

### 5.7 Deferred skills (not 0.5.0)

Specified in `backlog/Bora 0.5.5 Requirements.md`. Do not implement them in 0.5.0.

| Deferred skill | Superpowers analogue | Why wait |
|---|---|---|
| `bora-design` | `brainstorming` | Architecture conversation already exists in `AGENTS.md`; a dedicated skill comes after execute is proven |
| `bora-worktree` | `using-git-worktrees` | Isolation is a later operational concern |
| `bora-review` | `requesting-code-review` | Review against a plan is valuable once execute is proven |
| `bora-debug` | `systematic-debugging` | 0.5.0 stops after two verify failures; root-cause process is 0.5.5 |
| `bora-verify` | `verification-before-completion` | Partially inside `bora-tdd`; extract after we see agents claiming done without evidence |
| `bora-finish` | `finishing-a-development-branch` | Human still owns merge/PR in 0.5.0 |
| Subagent execute | `subagent-driven-development` | Optional 0.5.5 mode; default stays in-session |

Do not instruct agents to load Superpowers skills dynamically. Inside `docs/ai/<path>/`, Bora layout and commit contract win. Superpowers may still color conversation style, but plans are not written to `docs/superpowers/plans/` or into Requirements.

---

## 6. Implementation plan on the ticket

### 6.1 Location

```
docs/ai/<path>/
  (YYYY-MM-DD) {ProjectName}.md              ← what / why
  (YYYY-MM-DD) {ProjectName} Requirements.md ← spec (Tasks Breakdown → tickets)
  Status.md
  tickets/
    <ticket-id>.md                           ← work item + ## Implementation plan
```

No `plans/` directory. Init does not create one. `bora dev plan new` does not create a sidecar file.

### 6.2 Ticket body section

`bora dev ticket new` includes an empty section. The agent fills it via `bora-plan`.

```markdown
## Implementation plan

Status: draft
Current task:

### T01: {short title}
- **Files:** create/modify/test paths
- **Verify:** exact command and expected outcome (fail then pass)
- **Commit:** `{ticket-id} T01: {short title}`
- [ ] done

### T02: …
```

`Status:` in the section is mirrored to frontmatter `plan_status` by `bora dev plan set` (allowed: `draft | approved | in-progress | done | blocked`). During execute, `approved` is implied by project-level go; the agent may set `in-progress` without a separate human stamp.

Task IDs are `T01`, `T02`, … zero-padded, stable for the life of the ticket. Never renumber after a commit has used that id. Add `T04` at the end if the plan grows.

Each task is sized to **one commit**. Prefer an independently testable deliverable over a literal 2–5 minute clock.

### 6.3 Plan status vs ticket status

| `plan_status` | Ticket `status` (typical) | Meaning |
|---|---|---|
| *(no plan section / empty)* | `todo` | Not yet planned; allowed until execute reaches it |
| `draft` | `todo` | Agent is writing the plan; no code |
| `approved` | `todo` | Optional; unused during board execute |
| `in-progress` | `in-progress` | Tasks are being implemented |
| `blocked` | `blocked` | Cannot continue; Note explains why |
| `done` | `done` | All tasks checked; acceptance criteria met |

### 6.4 Who writes the plan

The **agent** writes the plan text on the ticket. The CLI updates `plan_status` / `current_task` and task checkboxes. There is no “generate Superpowers methodology” algorithm in Python.

---

## 7. Git commit contract

0.4.5 Commit criteria used `{task name}: {summary of what was done}`. 0.5.0 **replaces** that format for ticket work so commits are grepable.

**Format:**

```
{ticket-id} {task-id}: {task title}
```

Example:

```
20260814-01-add-share-extension-target T03: add app group entitlements
```

Rules:

- One git commit per completed plan task. Do not batch T01–T05 into one commit.
- The `{task title}` is the plan heading title. Extra context goes in the ticket Notes section.
- Bora still does **not** run `git commit` itself. The agent (or human) commits; the skill and `AGENTS.md` require the format.
- `git log --grep=20260814-01-add-share-extension-target` is that ticket's execution history. Do not add `docs/ai/logs/`.

Commit criteria in the Requirements template are updated to:

- Plan-task verification command passed (RED then GREEN).
- Change meets the matching requirement and acceptance criteria.
- Broader build/tests required by that project (for example `xcodebuild`) passed when the plan or Requirements say so.
- Commit message matches this contract.

---

## 8. Ticket schema (additive)

Existing required fields unchanged: `id`, `title`, `type`, `priority`, `status`, `created`.

New **optional** fields:

```yaml
plan_status: draft        # omit if no implementation plan yet
current_task: T03         # empty when not executing
```

No `plan:` path field (there is no sidecar file).

`subtasks:` remains for major queryable subtasks. Plan tasks (`T01`…) are **not** automatically duplicated into `subtasks`. 0.5.0 does not auto-migrate old checkbox subtasks into `T01` headings.

Tickets without these fields lint clean. Preferred API for plan fields is `bora dev plan set` / `bora dev plan task`, which edit the ticket and regenerate `Status.md`.

---

## 9. CLI (thin, agent-facing)

All plan commands take `<project_path>` first. Missing path is an error. They operate on the **ticket file**, not a `plans/` path.

### 9.1 `bora dev plan show <project_path> <ticket-id>`

Print the ticket's `## Implementation plan` section (or the whole ticket if the section is missing — then error with a hint to add it). Fuzzy ticket id.

### 9.2 `bora dev plan set <project_path> <ticket-id> <field> <value>`

Settable fields: `status` (writes `plan_status`), `current_task`.

Legal `status` values: `draft`, `approved`, `in-progress`, `done`, `blocked`.

Side effects:

- Update frontmatter and the `Status:` line in `## Implementation plan` if present.
- `status in-progress` sets ticket status to `in-progress` if it was `todo`.
- `status done` does **not** set ticket `done` (still `bora dev ticket set … status done` after acceptance criteria).
- `status blocked` sets ticket `blocked`.
- Always regenerate `Status.md`.

There is **no** `bora dev plan new`. The section is part of the ticket template; the agent fills it.

### 9.3 `bora dev plan task <project_path> <ticket-id> <task-id> <status>`

`<status>`: `todo` | `done`.

- `done`: check that task's checkbox, set `current_task` to the next unchecked `Tnn` (or empty), set `plan_status` to `in-progress` (or `done` if all tasks are checked).
- `todo`: uncheck (recovery).
- Regenerate `Status.md`.

The agent may also check boxes by editing Markdown; `lint` must accept either path.

### 9.4 No `bora dev execute` command

Execute is `bora-execute` (skill). Progress listing is `bora dev status` plus the chat summary in §5.5. Do not add `bora dev status --detailed`.

### 9.7 `bora dev upgrade`

Human-facing, repo-scoped, **dev profile only**. This is the mechanism that keeps `AGENTS.md` and the skill pack in sync with the installed CLI.

**Why it exists.** `AGENTS.md` is root-only operating instructions. The 0.5.0 gates (plan on the ticket, execute the board, commit contract, no continue prompt) live there as the fallback when a model has no skill loader. If someone upgrades the CLI but leaves a 0.4.5 `AGENTS.md`, agents will keep the old workflow. `skill install --force` refreshes skills only. `init --force` is too blunt (project briefing / Requirements / Status collisions). Upgrade is the dedicated, git-friendly refresh.

**Signature**

```
bora dev upgrade [--dry-run] [--agents-only] [--skills-only] [--force]
```

Missing `AGENTS.md` and no `.bora/profile.json` with `profile: dev`: error, tell them to `bora dev init` first.

**What it updates**

| Artifact | Action |
|---|---|
| Root `AGENTS.md` | Rewrite the **managed** region from the template shipped in this CLI (version stamped). Preserve **Project-specific instructions** (§10). |
| Skill pack | Same as `bora dev skill install --force` for every tool already installed (user-level and `--project` if present). Install the 0.5.0 four-skill pack, not a single `bora/SKILL.md`. Do not install tools the user never installed. |
| `.bora/profile.json` | Set `version` to this CLI’s version (0.5.0). Do not reset `initialized_at` or `profile`. |
| Project briefing, Requirements, `Status.md`, tickets | **Untouched.** New tickets from `ticket new` pick up the Implementation plan section; existing tickets stay valid without it (0.5.0 warning). |

**`AGENTS.md` layout** (what upgrade writes; `init` writes the same for new repos):

```markdown
# Agent Instructions

<!-- bora-managed:start version="0.5.0" -->
…full 0.5.0 operating instructions (briefing sequence, gates, commands)…
<!-- bora-managed:end -->

## Project-specific instructions

Add local rules below this heading. `bora dev upgrade` never overwrites
this section.
```

The HTML comments are the contract. The version attribute is how the CLI knows the file is stale. Visible prose in the managed block must not depend on agents reading the comments.

**Behavior**

1. **`--dry-run`:** print what would change (AGENTS.md stale/current, which skill paths would be rewritten). Exit 0. No writes.
2. **Managed file already present** (`bora-managed:start`): replace only the bytes between the start and end markers (including updating `version=`). Everything after `<!-- bora-managed:end -->` is preserved byte-for-byte, including a customized Project-specific section.
3. **Unmarked `AGENTS.md` (0.4.5 and earlier):**
   - If `AGENTS.md` has **uncommitted** git changes and `--force` is not set: exit 1 with “commit or stash `AGENTS.md`, then re-run; or pass `--force`.”
   - Otherwise write the new templated file (markers + empty Project-specific section). Git history / `git diff` is the backup — do not write `AGENTS.md.bak`.
   - Print: review `git diff AGENTS.md`; move any local rules into **Project-specific instructions**; commit when satisfied.
4. **`--agents-only` / `--skills-only`:** limit writes to that artifact.
5. **Skills:** if no skill is installed anywhere, print a hint to run `bora dev skill install <tool>` but do not fail the AGENTS.md update.
6. Bora does **not** `git commit`. The human commits the refreshed `AGENTS.md` (and project-level skills if any).

**Stale hint (other commands).** If `bora --version` is newer than the `version=` on `AGENTS.md` (or the file has no marker), `bora dev` commands other than `upgrade` print one stderr line and continue:

```
Note: AGENTS.md is not in sync with bora 0.5.0. Run `bora dev upgrade`.
```

Do not block ticket/status/lint/context/plan. Do not print the hint from `bora dev upgrade` itself.

**Not an upgrade path:** `bora dev init --force`, hand-copying templates, or re-running `skill install` alone (skills without AGENTS.md still leave chat-only / AGENTS.md-only models on the old workflow).

### 9.5 Lint additions

- If `## Implementation plan` is present: task headings match `^### T\d{2}: `; IDs unique; `current_task` if set must be a task id in the section; `plan_status` if set is an allowed value.
- Ticket `in-progress` with no implementation-plan section: **warning** in 0.5.0 (old workflows). Skill still forbids *new* implementation without a plan.
- Do not require every `todo` ticket to have a filled plan (execute fills it when the ticket is selected).
- Do not look for `docs/ai/<path>/plans/`.

### 9.6 `Status.md` additions

For in-progress and blocked tickets with `plan_status` / `current_task`:

```
- **20260814-01-add-target** Add Share Extension target [high] — plan in-progress · T03/T07
```

Keep the existing Done / In progress / Blocked / Todo buckets. Those buckets **are** the completed-vs-remaining list; `bora-execute` must print them in chat after each ticket, not only write the file.

`bora dev context` includes in-progress tickets as today (the ticket body already carries the plan section). Token budget still truncates.

---

## 10. Templates and `AGENTS.md`

- Root `AGENTS.md`: wrap the Bora-owned body in `bora-managed` markers with `version="0.5.0"`; append empty **Project-specific instructions**. Body still has skill-check gates; plan-on-ticket; human-light CLI; new commit format; after “go” run `bora-execute` across the board; between tickets show completed vs remaining; never ask to continue; never put the commit script in Requirements. `init` writes this shape; `upgrade` refreshes the managed region (§9.7).
- Skill pack: four `SKILL.md` files; bootstrap `description` trigger-only.
- Requirements template **Testing requirements**: prompt to name the project verify command(s) (for example `xcodebuild` for an iOS/macOS target, otherwise that project's equivalent). Ticket **Verify:** lines copy from here.
- Requirements template **Commit criteria**: verification + new commit format.
- Requirements template **Tasks Breakdown**: each item becomes a ticket; the implementation plan is written on the ticket when execute reaches it — not in this file.
- Ticket template: add empty `## Implementation plan` (with `Status:` / `Current task:` placeholders). Do not add `plan_status` to frontmatter until `plan set` runs.
- Do **not** create `plans/.gitkeep`.
- README: first-time workflow (§4.0); **Upgrading** (`pipx upgrade bora` then `bora dev upgrade`); `plan show/set/task`; skill pack including `bora-execute`; git contract; pointer to 0.5.5 for worktree/review/finish.

`bora dev init` still must **not** overwrite an existing root `AGENTS.md` unless `--force` (unchanged). `--force` remains the blunt scaffold overwrite — **not** the upgrade path. Existing projects use **`bora dev upgrade`** (§4.4, §9.7).

---

## 11. TDD policy (skill, not engine)

0.5.0 does not detect test runners or create test files from Python.

- Default for `feature` and `bug`: RED-GREEN-REFACTOR as in `bora-tdd`.
- `chore` / docs / config: TDD if there is behavior; otherwise one commit still mapped to a plan task with a verification step.
- `spike`: plan may say "no production code; capture notes."
- If the task's Verify command fails, the agent does not commit and does not advance `current_task`. After two failures on the same task, `bora-execute` stops and reports.

---

## 12. Error handling and resume

No log directory. Resume sources, in order:

1. `Status.md` (what's left on the board).
2. In-progress ticket: `plan_status`, `current_task`, task checkboxes, Notes.
3. `git log --grep=<ticket-id>`.

If interrupted mid-task: finish that task, then continue the board. Do not start T04 if T03 is unchecked and has uncommitted work. Do not skip remaining tickets.

`blocked`: set `plan_status` + ticket `blocked`, write a Note, then `bora-execute` tries the next *unblocked* ticket. If none, show the board (including Blocked) and stop.

---

## 13. Implementation tasks (building Bora 0.5.0)

1. **Ticket plan section** — template, parse `Tnn` headings/checkboxes, `plan_status` / `current_task` fields.
2. **`bora dev plan` commands** — `show`, `set`, `task` on the ticket file; Status regeneration. No `plan new`, no `plans/` resolver.
3. **Lint + Status.md + context** — §9.5–9.6.
4. **Skill pack** — four skills; install/uninstall/list; `--force` refreshes all four.
5. **AGENTS.md template** — managed markers + Project-specific section; `init` writes this shape on new repos.
6. **`bora dev upgrade`** — §9.7: refresh managed `AGENTS.md`, refresh already-installed skills, bump profile `version`, stale hint on other commands. Tests: unmarked 0.4.5 file, marked file with a custom tail preserved, dirty-file refuse, dry-run, skills-only/agents-only.
7. **README** — first-time workflow (§4.0); **Upgrading** from 0.4.5: `pipx upgrade bora` then `bora dev upgrade`; `plan show/set/task`; git contract.
8. **Tests** — template section, lint, status line, skill pack, backward-compatible tickets without plan fields.
9. **Manual skill-trigger pass** — walk §5.6 in at least two harnesses. Record gaps; do not block the release on perfect triggering everywhere.

---

## 14. Success criteria

0.5.0 is successful when:

1. A first-time engineer on an existing iOS/macOS repo can follow §4.0: `init` + `skill install`, write the briefing, approve Requirements in chat, say “go”, and not type `bora dev` again until they want a PR.
2. The agent works **through remaining tickets** without a continue prompt; after each ticket the human sees done vs remaining.
3. `git log` for a ticket is a readable sequence of `T01`, `T02`, … commits that match that ticket's implementation plan.
4. A crashed session resumes the in-progress ticket, then the rest of the board, from ticket files + `Status.md`.
5. Implementation plans are on tickets. Requirements is not used as a commit script. There is no `plans/` folder.
6. Existing 0.4.5 projects keep working without upgrade (old AGENTS.md, no plan section); `write` profile is unchanged.
7. After `pipx upgrade` + `bora dev upgrade`, `AGENTS.md` matches the 0.5.0 managed template, local text under Project-specific instructions is preserved when markers already existed, and the skill pack on disk matches this CLI. `init --force` is not required and is not documented as the upgrade path.

---

## 15. Decisions locked in this draft

- Thin CLI + thick skill. Execute is `bora-execute`, not a CLI engine.
- Bora-owned skills; no dynamic Superpowers load.
- **No `plans/` folder.** Implementation plan is a section on the ticket. Requirements remains the spec. Briefing remains what/why.
- Project-level “go” walks the whole board; between tickets, show completed vs remaining. Do not regress to “please do the next ticket?”
- Human-light: `init` + `skill install` + conversational Requirements approval + go. Existing repos add **`bora dev upgrade`** after a CLI upgrade. Skill install (or upgrade) is required for the loop to fire.
- **`bora dev upgrade`** is how `AGENTS.md` and skills stay in sync with the build. Managed markers + Project-specific section. Not `init --force`.
- Worktrees, design-skill, review, debug, verify-as-skill, finish/merge, subagent execute, and Cursor install → **0.5.5**.
- Commit message `{ticket-id} {task-id}: {title}`.
- Per-ticket plan approval is **not** required during execute; project-level go is enough.

## 16. Still open (do not block 0.5.0)

Nothing in this list is required to ship 0.5.0. All are specified or decided in `backlog/Bora 0.5.5 Requirements.md`:

- Cursor as an install target.
- Lint: in-progress without a plan becomes an error.
- Whether worktrees are default-on or consent-first.
