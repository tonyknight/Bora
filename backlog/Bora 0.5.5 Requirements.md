# Bora 0.5.5 Requirements

## Overview

0.5.0 gives a Bora project a working Superpowers *slice*: Requirements stay the spec, tickets hold `T01`…`Tn` implementation plans, `bora-tdd` makes those tasks into git commits, and `bora-execute` walks the **whole ticket board** after one “go,” showing completed vs remaining between tickets.

0.5.5 folds in the rest of the Superpowers *process* that 0.5.0 deliberately deferred — still **inside Bora’s project tree**, still thin CLI + thick skill, still no `docs/superpowers/` and no `plans/` folder.

Prerequisite: **0.5.0 has shipped** and been used on at least one real project. This release assumes the ticket plan section, `bora-plan` / `bora-tdd` / `bora-execute`, the commit contract, the between-ticket board display, and **`bora dev upgrade`** (managed `AGENTS.md` + skill pack refresh) already exist.

Upgrading 0.5.0 → 0.5.5 is the same human command, not a new one:

```bash
pipx upgrade bora
bora dev upgrade
```

That rewrites the `bora-managed` region of `AGENTS.md` to the 0.5.5 instructions (`bora-design`, worktree, review, debug, verify, finish) and refreshes the full ten-skill pack. Project-specific instructions, briefing, Requirements, and tickets are not overwritten.

The product bet does not change:

> Bora remains the project-driven system of record. Superpowers-shaped skills attach to briefing → Requirements → tickets → git. The human still types almost no `bora` commands. New skills fire at moments the 0.5.0 loop already has.

---

## 1. Design principles (additions to 0.5.0)

0.5.0 principles still hold. 0.5.5 adds:

1. **Same files, more gates.** Do not add spec/plan/review directories. Design output is Requirements. Review output is a section on the ticket (and Notes). Finish writes nothing new except git operations the human chose.
2. **New human gate only at the end.** 0.5.0 already has Requirements approval + go. 0.5.5 adds a **finish menu** (merge / PR / keep) when the board is complete. Do not reintroduce per-ticket “continue?” prompts.
3. **Worktrees are consent-first, then sticky.** Isolation protects `main` in a multi-target iOS/macOS repo. Ask once per project unless the human already declared a preference; remember it in `.bora/` or the project briefing so later tickets in the same execute run do not re-ask.
4. **Review the ticket, not every `T0n`.** Superpowers reviews every plan task. Bora’s grain is the ticket (the board unit, the grepable commit series). One review after the ticket’s last commit, before `status done`. Critical/important findings block moving to the next ticket.
5. **Debug before the second rewrite.** 0.5.0 stops after two verify failures. 0.5.5 loads `bora-debug` on the first unexpected failure so the agent finds root cause instead of flailing, then either continues the task or blocks the ticket.
6. **Subagents are optional.** Default execute stays in-session (0.5.0). If the harness can dispatch subagents, `bora-execute` *may* run one implementer per ticket. Never parallelize two tickets that touch the same files; `depends_on` still serializes.
7. **Still Bora-owned skills.** Do not vendor or dynamically load Superpowers. Encode the patterns. If Superpowers is also installed, Bora files and commit contract win inside `docs/ai/<path>/`.

---

## 2. Superpowers mapping (0.5.0 vs 0.5.5)

| Superpowers skill | Bora 0.5.0 | Bora 0.5.5 |
|---|---|---|
| `using-superpowers` | `bora` bootstrap | `bora` also skill-checks the new pack |
| `brainstorming` | Informal in `AGENTS.md` | **`bora-design`** — authors Requirements in sections, waits for agreement |
| `writing-plans` | `bora-plan` on the ticket | Unchanged (already on the ticket) |
| `test-driven-development` | `bora-tdd` | Unchanged; `bora-verify` backs the “don’t claim done” gate |
| `executing-plans` | `bora-execute` (in-session, whole board) | Same loop + worktree + review + debug + finish hook |
| `subagent-driven-development` | Out | **Optional** per-ticket subagent when the harness supports it |
| `using-git-worktrees` | Out | **`bora-worktree`** |
| `requesting-code-review` | Out | **`bora-review`** after each ticket |
| `receiving-code-review` | Out | Folded into `bora-review` (act on findings; no extra skill) |
| `verification-before-completion` | Partial in `bora-tdd` | **`bora-verify`** before ticket `done` and before finish |
| `systematic-debugging` | Two-strike stop | **`bora-debug`** on verify/build failure |
| `finishing-a-development-branch` | Human git | **`bora-finish`** menu when the board is complete |
| Visual companion, writing-skills, parallel dispatch across conflicting tickets | Out | Still out |

---

## 3. What 0.5.5 is (and is not)

### In scope

- Skill pack additions: `bora-design`, `bora-worktree`, `bora-review`, `bora-debug`, `bora-verify`, `bora-finish`.
- `bora` bootstrap updated to skill-check the new names.
- `bora-execute` updated: start with worktree (if consented), after each ticket run review + board display, on verify failure run debug, when the board is complete hand off to finish. Still no “continue?” between tickets.
- Optional subagent-per-ticket execute mode (same board order, same files).
- Cursor as a `bora dev skill install` target.
- Lint: ticket `in-progress` without `## Implementation plan` is an **error** (0.5.0 warning becomes error).
- README / `AGENTS.md` / first-time workflow: design skill before Requirements; finish menu after the board.

### Out of scope

- Python execute/review/worktree *engine*. Still skills + git + existing CLI.
- `plans/` folder, spec folder, `docs/ai/logs/`, `docs/superpowers/`.
- Coverage gates and test-framework auto-detection.
- Changing the three-document map (briefing / Requirements / ticket plan).
- Write profile.
- Requiring subagents (must work in-session).
- Parallel execution of tickets that share files.
- Visual companion, Superpowers telemetry, vendoring Superpowers.

---

## 4. Operator model (what changes for the first-time engineer)

0.5.0 path is unchanged until after “go” and at the very end.

```text
init + skill install
    → write briefing
    → bora-design: architecture conversation, fill Requirements, approve
    → “go”
    → bora-worktree (ask once if needed)
    → bora-execute walks tickets:
         plan → tdd → commits
         bora-verify → bora-review → show board → next ticket
         on failure: bora-debug (then continue or block)
    → board complete → bora-verify (full suite) → bora-finish menu
```

Human-typed commands are still:

- `bora dev init …`
- `bora dev skill install …` (now including `cursor`)

New conversational beats:

- During design: approve Requirements **in sections** if the agent presents them that way (architecture, then testing/commit criteria, then Tasks Breakdown). One final “approved” still suffices for small projects.
- After “go”: maybe one yes/no on a worktree. Then silence except board updates.
- When the board is done: pick **1 merge / 2 PR / 3 keep branch**.

They still do not type `plan`, `ticket`, `lint`, or `status`.

---

## 5. Skill pack (0.5.5 additions)

Install shape (full pack; 0.5.0 four plus six):

```
<tool-skills-root>/
  bora/SKILL.md
  bora-plan/SKILL.md
  bora-tdd/SKILL.md
  bora-execute/SKILL.md
  bora-design/SKILL.md
  bora-worktree/SKILL.md
  bora-review/SKILL.md
  bora-debug/SKILL.md
  bora-verify/SKILL.md
  bora-finish/SKILL.md
```

`bora dev skill install` installs the whole pack. Uninstall removes all bora-owned names. `--force` refreshes all. `bora dev upgrade` refreshes `AGENTS.md` (managed region, `version="0.5.5"`) **and** any already-installed pack paths — same contract as 0.5.0 §9.7. Descriptions remain trigger-only (`Use when…`, no workflow summary).

### 5.1 `bora-design` — brainstorming → Requirements

**Trigger intent:** Use when a bora project briefing exists and architecture is not yet agreed; when the Requirements file is still a placeholder; or when the user wants to discuss design before tickets. Do not use after Requirements are approved and execution has started, unless the user explicitly reopens design.

**Body:**

- Superpowers brainstorming, **output = the dated Requirements file**, not `docs/superpowers/specs/`.
- Read the briefing first. Ask questions (prefer one at a time). Propose 2–3 approaches with a recommendation. Present design in sections scaled to complexity; wait for agreement on contested sections.
- Only then fill Requirements: architecture, requirements, acceptance, **Testing requirements** (name the real command: `xcodebuild`, `pytest`, …), commit criteria, Tasks Breakdown.
- Hard gate: no tickets, no code, no `bora-execute` until the human approves Requirements.
- YAGNI: do not invent tickets for non-goals.
- If the project is too large for one Requirements file, help split into another `bora dev init` path (another project under `docs/ai/`), do not create a spec subdirectory.

### 5.2 `bora-worktree` — isolated git workspace

**Trigger intent:** Use when starting or resuming `bora-execute` on a bora project; when the user asks for an isolated branch/worktree; or before the first production commit of a project-level go. Do not create a nested worktree if already isolated.

**Body:**

- Follow Superpowers’ detect-existing-isolation → native harness tool → `git worktree` fallback. Never fight the harness.
- **Consent:** if no stored preference, ask once: isolate this project’s work? Yes → create; no → work in place for this project. Store the answer so later tickets in the same execute run do not re-ask.
- **Branch name** (git-friendly, derived from project path): `bora/<project_path-as-slug>` e.g. `bora/photoapp-ios-share-extension`. If it exists, reuse it (resume).
- Worktree directory: prefer `.worktrees/` at repo root if gitignored; else harness default. Do not commit the worktree.
- `docs/ai/<path>/` is the same files in the worktree (it is the same git). Tickets and Status updates happen there so `main` checkout is not dirty.
- Do not start execute on `main`/`master` without explicit consent (Superpowers rule, kept).
- Cleanup is **`bora-finish`**, not this skill.

Thin CLI (optional, agent-facing): none required in 0.5.5 if git + skill suffice. Do not add `bora dev worktree` unless the skill cannot be followed reliably without it. Prefer skill-only first.

### 5.3 `bora-review` — review the ticket before the next one

**Trigger intent:** Use when a bora ticket’s plan tasks are all checked and before marking the ticket `done`; when the user asks to review a ticket; or when `bora-execute` has just finished a ticket’s last commit. Do not use for architecture review (that is Requirements / `bora-design`).

**Body:**

- Review **this ticket’s commit range**: `git log --grep=<ticket-id>` from first `T01` commit through `HEAD` (plus uncommitted work if any — there should be none).
- Spec: Requirements (matching items) + ticket acceptance criteria + `## Implementation plan` (files named vs files touched).
- Quality: YAGNI, TDD evidence (RED then GREEN mentioned in the ticket or visible in history), commit messages match `{ticket-id} {task-id}: {title}`.
- Verdicts: **Critical** / **Important** / **Minor**.
- Critical or Important: do **not** mark the ticket `done`; do not start the next ticket. Fix (via `bora-tdd` / `bora-debug`) or ask the human. Minors go to ticket Notes.
- If the harness has subagents, dispatch a **fresh** reviewer with the diff (file, not pasted into the controller). If not, the same session reviews; still do not skip.
- Write a short `## Review` subsection on the ticket (date, verdict, findings). Git-diffable. No `reviews/` folder.

`bora-execute` must call this after the last plan task and **before** the completed-vs-remaining display that precedes the next ticket. If review fails, the board display still runs (ticket stays `in-progress` or becomes `blocked`), then execute stops or continues with other *unblocked* tickets per 0.5.0 pick order.

### 5.4 `bora-debug` — root cause before the rewrite

**Trigger intent:** Use when a plan-task verify command fails, a build fails, or behavior is unexpected during bora execute/TDD; before proposing a second implementation attempt. Do not use for the expected RED failure of a newly written test.

**Body:**

- Superpowers four-phase systematic debugging: investigate, pattern analysis, hypothesis, fix. No fix without root cause.
- Expected RED (new test failed as designed) is **not** this skill — that is `bora-tdd`.
- Record root cause in the ticket Notes. If the plan task is wrong, amend the plan (add `Tnn`, do not renumber committed ids) rather than silently expanding scope.
- After a fix, `bora-verify` that task’s command, then continue execute.
- If root cause is a Requirements hole, **stop execute**, reopen `bora-design` with the human — do not invent architecture in the ticket.

Replaces 0.5.0’s blunt “two failures then stop” as the first response. After debug, a second failure on the same hypothesis still stops and blocks.

### 5.5 `bora-verify` — evidence before done / finish

**Trigger intent:** Use before marking a bora plan task complete, before marking a ticket `done`, before claiming tests pass, or before `bora-finish`. Do not use as a substitute for TDD’s RED step.

**Body:**

- Iron law: no completion claim without a **fresh** run of the named command in this turn.
- Task complete → that task’s **Verify:** line.
- Ticket `done` → task verifies plus ticket acceptance criteria plus any extra command Requirements Commit criteria named for “ticket done.”
- Board complete / finish → the **project** suite from Requirements Testing requirements (e.g. full `xcodebuild` for affected schemes).
- Paste or quote enough of the output to show pass/fail. “Should pass” is a failure of this skill.
- `bora-tdd` and `bora-finish` both require this skill; extracting it makes the trigger fire when agents skip TDD but still want to close a ticket.

### 5.6 `bora-finish` — integrate when the board is complete

**Trigger intent:** Use when a bora project has no remaining unblocked tickets (all `done`, or only `blocked` the human accepted as out of scope), verification of the project suite has passed, and the user needs to decide how to integrate. Use also when the user says the work is done / merge / PR. Do not use after a single ticket if others remain.

**Body:**

- Run `bora-verify` on the project suite first. Failures: no menu.
- Confirm base branch with the human if ambiguous.
- Present Superpowers’ menu, adapted:

```
Board complete for <project_path>. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
```

- Detached HEAD / externally managed worktree: omit local merge (options 2 and 3 only).
- Discard only if the human explicitly asks.
- Execute the choice; then clean up a worktree this session created (provenance: only remove what `bora-worktree` created).
- Do not mark tickets `done` here — they should already be `done`. Update a ticket Note if merge/PR URL exists.
- Bora still does not become a git porcelain CLI. The **agent** runs `git` / `gh`. No `bora dev finish` command unless we later find agents cannot follow the menu without one.

### 5.7 `bora-execute` (changes from 0.5.0)

Keep 0.5.0 board walk, pick order, between-ticket display, no continue prompt.

Insert:

1. On start: `bora-worktree`.
2. Per ticket: `bora-plan` → `bora-tdd` (with `bora-debug` on unexpected failure, `bora-verify` on each task).
3. After last task: `bora-verify` (ticket) → `bora-review` → ticket `done` only if review is clean or minors-only → **show completed vs remaining** → next ticket.
4. Board complete: `bora-verify` (project) → `bora-finish`.

**Optional subagent mode** (same skill, extra section):

- Use only if the harness can dispatch subagents **and** the human did not forbid them.
- One implementer subagent **per ticket** (not per `T0n`, not two tickets in parallel). Controller keeps the board, Status.md, and review.
- Implementer gets: project path, ticket file path, Requirements path, commit contract, TDD iron law. It does not inherit chat history.
- On `DONE`, controller runs `bora-review`. On `BLOCKED`, controller follows 0.5.0 blocked rules.
- If subagents are unavailable, in-session execute is correct, not a fallback apology loop.

### 5.8 `bora` bootstrap (changes)

Skill-check list includes all 0.5.5 names. First-time: `bora-design` before Requirements. After go: `bora-execute` (which pulls worktree/review/debug/verify/finish). Human-light and plan-on-ticket rules unchanged.

---

## 6. Trigger matrix (additions)

| Situation | Must load | Must not skip |
|---|---|---|
| Briefing exists, Requirements still placeholder | `bora`, `bora-design` | Filling Requirements from the briefing alone; creating tickets |
| Requirements approved, “go” | `bora-execute` (starts `bora-worktree`) | First commit on `main` without consent |
| Expected RED on a new test | `bora-tdd` | `bora-debug` |
| `xcodebuild`/verify failed unexpectedly | `bora-debug` | Immediate rewrite; claiming done |
| Last `T0n` committed on a ticket | `bora-verify`, `bora-review` | Marking `done` and jumping to the next ticket |
| Ticket `done`, others remain | `bora-execute` board display, next ticket | Finish menu; “continue?” |
| All tickets `done` | `bora-verify` (project), `bora-finish` | Silent stop with a dirty branch and no menu |
| Human pastes review comments | `bora-review` (receiving: fix Critical/Important) | Arguing without reading the diff |

---

## 7. CLI and files

### 7.1 CLI

- Extend `bora dev skill install` with **`cursor`** (and keep `claude`, `opencode`, `all`).
- No new human-facing commands. **`bora dev upgrade` already exists in 0.5.0**; 0.5.5 only ships a newer managed `AGENTS.md` body (`version="0.5.5"`) and a larger skill pack for that command to write.
- Agent-facing: still `plan show/set/task`, `ticket *`, `status`, `lint`.
- Do **not** add `bora dev execute`, `bora dev finish`, or `bora dev worktree` in 0.5.5 unless implementation proves the skill cannot drive git alone. Default is skill-only.

### 7.2 Ticket body

Optional `## Review` section appended by `bora-review`. Lint ignores unknown `##` sections other than requiring `## Implementation plan` when `status` is `in-progress`.

### 7.3 Lint (stricter)

- Ticket `in-progress` without a filled `## Implementation plan` (at least one `### Tnn:` heading): **error**.
- `plan_status` / `current_task` rules from 0.5.0 remain.
- Still no `plans/` resolver.

### 7.4 Stored worktree preference

Minimal, git-friendly: a key on the existing project briefing frontmatter, e.g. `worktree: true|false`, set after the first consent. Do not add a new config file if frontmatter suffices. Repo-global `.bora/profile.json` must **not** force all projects to isolate.

### 7.5 Status.md

No new buckets. After review findings that block a ticket, status is `blocked` or stays `in-progress` with a Note; the between-ticket display already has a Blocked list.

---

## 8. Git and commits

0.5.0 commit contract unchanged: `{ticket-id} {task-id}: {title}`.

Review-fix commits on the same ticket continue the sequence (`T04` added if needed, or a new task `T03b` is **forbidden** — use `T04`). Finish merge/PR is human-chosen; commit messages for merge are git defaults / `gh pr` title, not a Bora format.

Branch `bora/<slug>` is the execute workspace. Ticket files and Status.md commit as part of the same history as code (agent may commit docs with the task they belong to, or with T01 if the plan was written then). Prefer: plan-section updates ride along with the `T0n` commit they describe, so git stays aligned.

---

## 9. Templates and docs

- `AGENTS.md`: bump managed `version="0.5.5"`; design skill before Requirements; worktree consent; review before next ticket; debug on unexpected failure; verify before done; finish menu when the board is complete; still no continue prompt. Existing 0.5.0 repos pick this up via `bora dev upgrade`, not `init --force`.
- README first-time workflow: insert design and finish; mention Cursor install; mention optional worktree.
- Requirements template: Testing requirements must name commands (already prompted in 0.5.0; 0.5.5 `bora-verify` / `bora-finish` depend on that being filled).
- Skill pack templates for the six new skills; bootstrap descriptions updated.

---

## 10. Implementation tasks (building Bora 0.5.5)

1. **Cursor install target** — registry + tests; `all` includes it.
2. **Lint error** for in-progress without a plan section.
3. **`bora-design` skill** + `AGENTS.md` briefing sequence points at it.
4. **`bora-worktree` skill** + briefing `worktree:` preference.
5. **`bora-verify` + `bora-debug` skills**; `bora-tdd` / `bora-execute` cross-links.
6. **`bora-review` skill** + ticket `## Review` convention.
7. **`bora-finish` skill**; `bora-execute` handoff when the board is clear.
8. **`bora-execute` rewrite** in the skill body (hooks above; optional subagent section).
9. **Bootstrap `bora` skill** — skill-check all ten names; trigger-only description still accurate.
10. **Upgrade template** — `bora dev upgrade` writes `version="0.5.5"` and the ten-skill pack; tests that a 0.5.0 marked `AGENTS.md` keeps Project-specific instructions.
11. **README** — 0.5.5 workflow; mapping table; Cursor; upgrading is still `pipx upgrade bora` then `bora dev upgrade`.
12. **Manual trigger pass** — walk §6 in Cursor and one other harness on a small real project (not only Bora’s own tests).

---

## 11. Success criteria

0.5.5 is successful when:

1. A first-time engineer still types only init + skill install + chat, and additionally gets a design conversation that fills Requirements **before** tickets, a finish menu when the board is done, and (if they consented) work not committed on `main`.
2. After each ticket, they still see completed vs remaining; they also see a review verdict before the next ticket starts.
3. Unexpected test/build failure produces a root-cause Note, not an immediate rewrite.
4. Claims of “tests pass” / “ticket done” / “board complete” are backed by a command run in that turn (`bora-verify`).
5. Cursor can receive the pack via `bora dev skill install cursor`.
6. No `plans/` folder, no Superpowers directory, no new human command palette (upgrade already exists).
7. In-session execute still works without subagents.
8. `bora dev upgrade` from a 0.5.0 repo refreshes managed `AGENTS.md` to 0.5.5 and the ten-skill pack without touching Requirements or tickets.

---

## 12. Decisions locked in this draft

- 0.5.5 is process depth on the 0.5.0 file model, not a new tree.
- Skills: design, worktree, review, debug, verify, finish; optional subagent-per-ticket.
- Review grain = ticket, not `T0n`.
- Worktrees = consent-first, preference stored on the briefing.
- Finish menu = the new human gate; still no per-ticket continue prompt.
- Cursor install in this release.
- In-progress without a plan → lint error.
- No `bora dev finish` / `worktree` / `execute` CLI unless skills fail in practice.

## 13. Later than 0.5.5

- Parallel tickets with disjoint file sets (`dispatching-parallel-agents`).
- Per-task (not per-ticket) review, if ticket reviews miss too much.
- Visual companion for `bora-design`.
- Coverage / runner detection.
- Write-profile analogue (out of scope for this Superpowers fold-in).
