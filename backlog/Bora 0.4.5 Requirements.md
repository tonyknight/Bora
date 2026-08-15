# Bora 0.4.5 Requirements

## Hierarchical Dev Project Structure

### Overview
Bora `dev` profile currently scaffolds a single flat project at `docs/ai/` (`Project.md`, `Architecture.md`, `Tasks.md`, `tickets/`). For large codebases with multiple target outputs, this does not scale. `0.4.5` consolidates all scaffolding and ticketing on a per-project basis under a hierarchical path `docs/ai/<Codebase>/<Target>/<Project>/...`, enabling multiple concurrent projects in one repo in a git-friendly tree.

Each project uses two dated Markdown files whose names include the project name, plus an auto-generated status dashboard:

```
docs/ai/<path>/
  (YYYY-MM-DD) {ProjectName}.md                 ← project briefing (was Project.md)
  (YYYY-MM-DD) {ProjectName} Requirements.md    ← architecture + spec (was Architecture.md + Implementation Plan.md)
  Status.md                                     ← auto-generated dashboard (was Tasks.md)
  tickets/
```

Square brackets in this document (`[ProjectName]`) are placeholders, not literal characters in filenames. `{ProjectName}` is the last segment of `<project_path>` (for example `Gallery Refactor`).

---

## Changes from 0.4.0 (unreleased)

0.4.0 was never shipped. This document supersedes it. Deltas:

1. **Consolidate Architecture.md and Implementation Plan.md** into a single dated Requirements file. After the agent reads the project briefing, it discusses architecture with the human, then fleshes out the Requirements document. Tickets are created from that document, and may be executed by one or more agents.
2. **Rename Tasks.md → Status.md.** Same auto-generated dashboard behavior; `bora dev status <project_path>` still regenerates it. The bora skill calls this command to refresh job status.
3. **Date-stamp the project briefing** as `(YYYY-MM-DD) {ProjectName}.md`, matching the Requirements naming convention. (`YYYY-MM-DD`, not `YYY-MM-DD`.) Filename dates are frozen at init; `last_reviewed` tracks freshness.
4. **Rewrite root AGENTS.md** (dev-profile template) for the hierarchical layout and the discuss-then-Requirements-then-tickets workflow.
5. **Remove `bora dev decision`.** Decisions are edited into the Requirements file. The init template includes placeholder sections for Requirements, Acceptance criteria, Testing requirements, and Commit criteria (subtask completion tests, requirement met, build tests passed; commit message is `{task name}: {summary}`).

---

## 1. Objectives

1. Replace singleton `docs/ai/` scaffolding with hierarchical `docs/ai/<path>/` projects.
2. Make `bora dev init` require an explicit hierarchical path and scaffold entirely inside that path.
3. Enable multiple independent projects to coexist without Bora-side active-project tracking.
4. Consolidate the legacy `bora dev project` versioning command into frontmatter inference at `init` time via optional tags.
5. Use a single per-project Requirements document as the architecture record and the spec source. Ticket creation flows from it. Remove the `/specs` concept and do not scaffold separate `Architecture.md` or `Implementation Plan.md` files.
6. Scope all `dev` operations (`ticket`, `status`, `context`, `lint`) strictly to the referenced project directory (per-project `Status.md`, per-project `tickets/`).
7. Scope change to `dev` profile only. `write` profile is untouched. No migration or backwards-compatibility handling for the old flat layout; documentation is updated to the new model.

---

## 2. Hierarchical Path Model

### 2.1 Path form
- `bora dev init <project_path> [--tags <csv> | <bracket-list>]`
- `<project_path>` is a slash-delimited hierarchy: `Codebase/Target/Project` at minimum, extensible to depth `N >= 2`.
- `{ProjectName}` is the last path segment. Spaces in a segment are part of the name.
- Example: `bora dev init QromaCore/Hamburg/Gallery\ Refactor` or quoted `bora dev init "QromaCore/Hamburg/Gallery Refactor"` on 2026-08-14 yields:

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

- Deeper example: `bora dev init Acme/Platform/Auth/OAuth Refresh` is valid (depth 4). `{ProjectName}` is `OAuth Refresh`.

### 2.2 Validation rules
- Minimum depth 2: at least one `/` must be present. `bora dev init Foo` or `bora dev init ""` is rejected with a clear error and non-zero exit.
- Accept quotes: if the raw argument is wrapped in single or double quotes (as the shell presents it), treat the quoted span as literal. Spaces inside a segment are one tree level, not additional segments: `Gallery Refactor` is one directory name.
- Accept bracket-wrapped optional tags (see §3.2) but do not treat brackets as path characters.
- Reject: empty segments (`a//b`, leading `/`, trailing `/`), segments that are `.` or `..` or empty/whitespace-only, absolute paths, or any segment containing path traversal.
- If the resolved `docs/ai/<path>/` already exists, build into that path: create missing scaffold files but check for collisions file-by-file. Collision detection must match by **role**, not only today's exact filename: any existing project-briefing file or Requirements file for this `{ProjectName}` (see §2.4) counts as a collision, as does an existing `Status.md`. Without `--force`, list collisions and exit 1 without overwriting. With `--force`, overwrite the matched files (do not leave a second dated copy for the same role).
- Sanitization happens before any filesystem join; error messages name the violated rule.

### 2.3 Dated filename convention
- Format: `(YYYY-MM-DD)<space>{ProjectName}.md` and `(YYYY-MM-DD)<space>{ProjectName} Requirements.md`.
- Parentheses around the ISO date match existing bora date-prefix style (project archives, Summary archives).
- `{ProjectName}` is used as-is (including spaces). Literal `[` `]` are not written to disk.
- The date written at `init` is `date.today()`. The filename date is **not** rewritten on later edits; freshness is tracked via `last_reviewed` in frontmatter.
- Resolvers that need the project briefing or Requirements file **discover** them by scanning the project directory (see §2.4). They must not assume today's date is in the filename.

### 2.4 Resolver helpers
Introduce project-scoped path resolvers (replacing flat constants):

- `project_dir(root, project_path) -> docs/ai/<path>/`
- `project_file(root, project_path) ->` discovered `(YYYY-MM-DD) {ProjectName}.md` in that directory
- `requirements_file(root, project_path) ->` discovered `(YYYY-MM-DD) {ProjectName} Requirements.md`
- `status_file(root, project_path) -> docs/ai/<path>/Status.md`
- `project_tickets_dir(root, project_path) -> docs/ai/<path>/tickets/`

Discovery regexes (filenames only, not full paths):

- Requirements: `^\(\d{4}-\d{2}-\d{2}\) (.+) Requirements\.md$` where group 1 must equal `{ProjectName}`
- Project briefing: `^\(\d{4}-\d{2}-\d{2}\) (.+)\.md$` where group 1 equals `{ProjectName}` **and** the name does not end with ` Requirements.md`

If more than one file matches a role, use the latest date in the filename. If none match, resolvers used by `init` construct today's names; other commands error with a message that names the missing role and the expected pattern.

Do **not** provide `architecture_file`, `tasks_file`, `implementation_plan_file`, or a constant `PROJECT_FILE = "docs/ai/Project.md"` for `dev` callers. These replace direct use of `DOCS_DIR` / `TICKETS_DIR` / `PROJECT_FILE` in all `dev` callers.

---

## 3. CLI Changes

### 3.1 `bora dev init <project_path> [--tags ...] [--force]`
Replaces the old flat `bora dev init [tools]`.

- Signature: `bora dev init <project_path> [--tags <csv>] [--force]`
- `<project_path>` is required and must pass §2.2 validation.
- `--tags` is optional. Two equivalent forms are accepted:
  - `--tags Codebase,"Release Train",Project`
  - Trailing bracket form ` [Codebase,Release Train,Project]` (normalized to `--tags` internally for backwards ergonomics).
  Tags map 1:1 to path segments in order. If provided, count must equal depth; otherwise error with hint.
- `--force` allows overwriting existing scaffold files in an existing project directory (see §2.2 collision-by-role).
- Behavior:
  1. Validate `<project_path>` via §2.2.
  2. Resolve `docs/ai/<path>/`; `mkdir -p` as needed.
  3. If any target scaffold file exists (by role) and `--force` not set, abort with collision list.
  4. Ensure `.bora/profile.json` exists at repo root with `profile: dev` (create if absent). Do not create per-project `.bora` dirs.
  5. Write per-project scaffold (see §4).
  6. Print created paths relative to repo root.

- Skill install variadic `tools` from the old `dev init` is removed from this signature to avoid ambiguity with path segments. Use `bora dev skill install <tool>` separately.

### 3.2 Tag-inferred frontmatter (consolidates `bora dev project`)
The legacy `bora dev project` command (which archived `Project.md` to `docs/ai/Projects/` and scaffolded a new dated file) is removed. Its frontmatter-versioning role is consolidated into `init`:

- At `init`, frontmatter keys for the hierarchy are inferred from `<project_path>` segments plus optional `--tags` labels.
- Always write `hierarchy: [segment, ...]` on both the project briefing and the Requirements file.
- If `--tags` is supplied, also write slugified tag keys mapped 1:1 to segments, and `tags: [...]`.
- Example: `bora dev init QromaCore/Hamburg/Gallery\ Refactor --tags Codebase,"Release Train",Project` writes this frontmatter on `(YYYY-MM-DD) Gallery Refactor.md`:
  ```yaml
  codebase: QromaCore
  release_train: Hamburg
  project: Gallery Refactor
  hierarchy: [QromaCore, Hamburg, Gallery Refactor]
  tags: [Codebase, Release Train, Project]
  last_reviewed: 2026-08-14
  focus: ""
  ```
- If `--tags` is omitted, write `hierarchy` only (no invented `level_1` keys).
- Tag keys are slugified for YAML: lowercase, spaces to underscores (`Release Train` → `release_train`).
- `bora dev project` is removed from `bora dev --help`. If kept, it becomes a hidden stub that prints `bora dev project is removed in 0.4.5 — use bora dev init <path> --tags ...` and exits 1.

### 3.3 Project-scoped commands
All `dev` commands that previously operated on the singleton `docs/ai/` become project-scoped and require the project path as a required positional argument (consistent with `init`):

- `bora dev ticket new <project_path> "<title>" [--type --priority --parent --no-edit]`
- `bora dev ticket list <project_path> [--status --type --priority --blocked]`
- `bora dev ticket show <project_path> <ticket_id>`
- `bora dev ticket set <project_path> <ticket_id> <field> <value>`
- `bora dev ticket note <project_path> <ticket_id> "<text>"`
- `bora dev ticket subtask <project_path> <ticket_id> <subtask_id> <status>`
- `bora dev status <project_path>` — regenerates `docs/ai/<path>/Status.md` only. Command name stays `status`; output filename is `Status.md`. No root `docs/ai/Status.md` (or `Tasks.md`) aggregation. Ticket mutations that already regenerate the dashboard continue to do so, writing `Status.md`.
- `bora dev context <project_path> [--budget N]` — assembles briefing from root `AGENTS.md` plus, inside `docs/ai/<path>/` only: the dated project briefing, the dated Requirements file (if present), `Status.md`, and in-progress/blocked tickets. Do not read other projects.
- `bora dev lint <project_path>` — validates only `docs/ai/<path>/tickets/`; `parent`/`depends_on` must reference ids within the same project's `tickets/` (cross-project refs are errors).

- `bora dev decision` is **removed** (not retargeted). Architecture decisions are written into the Requirements document by the human or agent during the architecture discussion. If kept at all, it is a hidden stub that prints `bora dev decision is removed in 0.4.5 — record decisions in the project's Requirements file` and exits 1. It must not appear in `bora dev --help`.

- Missing or invalid `<project_path>` exits 1 with usage hint.
- Bora does not maintain an active-project pointer. The human references the correct `docs/ai/<path>/(YYYY-MM-DD) {ProjectName}.md` when starting an agent session; that directory defines the scope. `AGENTS.md` is updated with a safeguard noting agents must only read/write inside the referenced project directory (see §4.4).

- `bora dev skill install/list/uninstall` remains global (operates at repo root or user level, not per-project). The **skill template text** is updated to the 0.4.5 workflow (hierarchical paths, Requirements-driven tickets, `Status.md`). Install/uninstall mechanics are unchanged.

---

## 4. File Layout and Templates

### 4.1 Per-project scaffold
Each `bora dev init <path>` creates:

```
docs/ai/<path>/
  (YYYY-MM-DD) {ProjectName}.md
  (YYYY-MM-DD) {ProjectName} Requirements.md
  Status.md
  tickets/
    .gitkeep
```

- No `Architecture.md`, no `Implementation Plan.md`, no `Project.md`, no `Tasks.md`, no `chapters/`, and no top-level `docs/ai/Project.md` is created by this command.
- No `docs/ai/specs/` is created. That directory, if present from older versions, is left untouched but no longer referenced by new projects.
- The Requirements file is scaffolded as a **placeholder template** with empty section headings (see §4.3). The agent must not fill those sections until after the architecture discussion described in §4.4.

### 4.2 Project briefing — `(YYYY-MM-DD) {ProjectName}.md`
Replaces `Project.md`.

- Frontmatter: inferred hierarchy keys from §3.2 plus `last_reviewed` (today) and `focus` (empty string).
- Body retains standard sections: Background, Goals, Non-goals, Target users, User stories, Constraints, Success criteria. Content is placeholder until human and agent confer.
- This file is the session entry point the human points the agent at. It describes **what** is being built and **why**. It is not the architecture or the implementation spec.

### 4.3 Requirements — `(YYYY-MM-DD) {ProjectName} Requirements.md`
Replaces both `Architecture.md` and `Implementation Plan.md`.

- Location example: `docs/ai/QromaCore/Hamburg/Gallery Refactor/(2026-08-14) Gallery Refactor Requirements.md`.
- Init writes `REQUIREMENTS_MD_TEMPLATE`: a placeholder with section headings and one-line prompts, not filled-in content. After the human and agent agree on architecture, the agent fleshes out this file as the complete project spec.
- Template sections (single document, no split). Init must create all of these headings:

  1. Overview
  2. Goals
  3. Non-goals
  4. Architecture — Components, Data model, Key flows (filled after the architecture discussion)
  5. Requirements — functional and non-functional requirements
  6. Acceptance criteria
  7. Testing requirements
  8. Commit criteria — per-subtask completion gate and commit-message rule (see below)
  9. Tasks Breakdown — the work items that become tickets
  10. Risks and assumptions
  11. Open questions

- **Commit criteria** is not a vague definition of done. It is a checklist the agent must satisfy before treating a subtask (or ticket) as complete and before making a git commit. The Requirements template must prompt for, and AGENTS.md / the skill must enforce:

  1. **Subtask completed** — a defined set of tests or checks that show this subtask is actually finished (not merely coded).
  2. **Meets the requirement** — the change satisfies the matching item under Requirements and Acceptance criteria.
  3. **Build tests passed** — where the target is a compiled project (for example macOS or iOS), the relevant build and test commands have been run and passed. Where there is no native build, the project's equivalent verification (unit tests, lint, etc.) has passed.
  4. **Commit message** — `{task name}: {summary of what was done}`. The task name is the ticket or subtask title; the summary is one or two sentences of what changed. Example: `Implement login flow: Wired AuthService to the session store and added failing-credential tests.`

  Bora does not create git commits. This is agent workflow: do not mark the ticket/subtask `done` and do not commit until the checklist above is true. The Commit criteria section of each project's Requirements file should be filled with the concrete commands and checks for that project (e.g. `xcodebuild`, `pytest`) during the architecture/requirements discussion.

- There is no `bora dev decision` command. If a decision needs to be recorded, the human or agent edits the Requirements file directly (typically under Architecture or Open questions).
- Ticket creation is driven from **Tasks Breakdown**: when it is time to implement, the agent (or the human directing several agents) creates tickets from that section. One Requirements document may produce tickets for one agent or several; Bora does not add a ticket-claim or agent-assignment command in 0.4.5.
- No root `docs/ai/Architecture.md` is created for hierarchical projects.

### 4.4 AGENTS.md (root — single file, must be updated)

`AGENTS.md` stays at the repo root. It is the only agent instruction file. The following exact changes are required (implemented via `bora/templates.py:AGENTS_MD` and written once when a repo first gets a `dev` init; `bora dev init <path>` must not overwrite an existing root `AGENTS.md` unless `--force` is given):

1. **Header / Philosophy** — Change the shared-workspace description from "Documentation in `docs/ai/` is your shared workspace" to: "Documentation in `docs/ai/<Codebase>/<Target>/<Project>/` is your per-project shared workspace. Multiple projects may coexist under `docs/ai/`." State that the project briefing and Requirements files are dated and named after the project, and that `Status.md` is auto-generated.

2. **Briefing sequence** — Replace the flat 5-step sequence with:

   ```
   1. AGENTS.md (root — this file)
   2. The human-referenced project briefing:
      docs/ai/<path>/(YYYY-MM-DD) {ProjectName}.md
   3. Discuss architecture with the human before writing Requirements.
      Do not skip this conversation. Do not fill in the Requirements
      file from Project.md alone.
   4. After agreement, author/update:
      docs/ai/<path>/(YYYY-MM-DD) {ProjectName} Requirements.md
   5. docs/ai/<path>/Status.md  (read only — never hand-edit)
   6. When implementing: create tickets from the Requirements
      Tasks Breakdown. Tickets may be worked by one or more agents.
   7. docs/ai/<path>/tickets/<id>.md as the active work demands
   8. If budget-constrained, run `bora dev context <path> --budget N`
   ```

3. **Scope guardrail** — New subsection after Briefing sequence:

   > **Scope guardrail:** The human will reference the correct `docs/ai/<path>/(YYYY-MM-DD) {ProjectName}.md` when starting the session. Only read and write files inside that project's directory (`docs/ai/<path>/` and its `tickets/`). Do not operate on other `docs/ai/<other>/` projects, the legacy flat `docs/ai/Project.md`, or the repo root unless the human explicitly references them. `Status.md` is per-project only — do not expect or create a root `docs/ai/Status.md` or `docs/ai/Tasks.md` aggregation. All `bora dev` commands require the explicit `<project_path>` argument to enforce this.

4. **Workflow — Orient, then Requirements, then tickets** (replaces "Starting a new feature" as the primary path):

   1. Read the referenced project briefing and confirm scope with the human.
   2. Discuss architecture: components, data model, key flows, constraints, non-goals. Propose options; wait for agreement.
   3. Write or update `(YYYY-MM-DD) {ProjectName} Requirements.md`: architecture, requirements, acceptance criteria, testing requirements, commit criteria, Tasks Breakdown, risks, and open questions. Bump `last_reviewed`.
   4. Only then create tickets from the Tasks Breakdown: `bora dev ticket new <project_path> "<title>"`. `<project_path>` is the same value passed to `bora dev init`. Use `--parent` when a breakdown item splits.
   5. Tickets may be assigned in conversation to one or more agents; each agent still stays inside this project directory and updates only the tickets it is working.
   6. After ticket changes, run `bora dev status <project_path>` (the skill does this) so `Status.md` reflects current work.
   7. Before marking a ticket or subtask `done`, and before any git commit, satisfy **Commit criteria** in the Requirements file: the subtask's completion tests pass, the change meets the requirement, and build/tests pass (including platform builds such as macOS/iOS when that is the target). Commit message format: `{task name}: {summary of what was done}`.

5. **Workflows — Resuming work** — Update `bora ticket show / set / note / subtask`, `bora status`, `bora context`, `bora lint` examples to include `<project_path>` and `Status.md`. Example: `bora dev ticket show QromaCore/Hamburg/Gallery\ Refactor 20260811-01` and `bora dev status QromaCore/Hamburg/Gallery\ Refactor`.

6. **Workflows — Marking a ticket complete** — Before `bora dev ticket set <project_path> <id> status done` (or setting a subtask to `done`), the agent must run the Commit criteria checks in the Requirements file. Then, if the human wants a commit, use message `{task name}: {summary of what was done}`. Do not commit if build or completion tests failed.

7. **Workflows — Recording decisions** — Remove `bora decision new` / `bora dev decision new`. Instruct the agent to edit the Requirements file directly after agreeing with the human.

8. **Frontmatter reference** — Update the ticket path example from `docs/ai/tickets/` to `docs/ai/<path>/tickets/` and note ticket IDs are unique per-project, not repo-global.

9. **Validation** — Update `bora lint` example to `bora dev lint <project_path>`. After any ticket write, run lint then `bora dev status <project_path>`.

10. **Diagram** — Add a tree diagram of the hierarchical layout including the dated briefing, dated Requirements, `Status.md`, and `tickets/`.

11. **Do not hand-edit Status.md.** Same rule as the old Tasks.md: update tickets, then regenerate.

The installed bora **skill** (`bora/skill.py` SKILL.md template) must carry the same briefing sequence, scope guardrail, Requirements-then-tickets workflow, Commit criteria (do not mark done or commit until completion tests, requirement match, and build tests pass; commit message `{task name}: {summary}`), and `bora dev status <project_path>` → `Status.md` behavior, so agents that load the skill instead of (or in addition to) `AGENTS.md` get identical instructions.

### 4.5 Tickets and Status.md
- Tickets live strictly under `docs/ai/<path>/tickets/<id>.md`. Ticket IDs remain `YYYYMMDD-NN-slug`; uniqueness is enforced per-project (lint checks within that project's `tickets/`).
- `Status.md` is per-project at `docs/ai/<path>/Status.md`, auto-generated by `bora dev status <path>` from that project's tickets and the project briefing's `focus` field. Dashboard content and grouping stay the same as today's `Tasks.md` (in-progress, blocked, todo, recently done, focus). Only the filename and all user-facing references change.
- There is no root `docs/ai/Status.md` or `docs/ai/Tasks.md` aggregation. `bora dev status` without a path is an error.

---

## 5. Configuration

- `.bora/profile.json` remains at repo root with `profile: dev` (or `write`). No per-project `.bora` directories.
- `.bora/project.json` active-pointer (`active: Project.md`) is no longer used for `dev` hierarchical projects and must not be consulted to resolve files. Prefer removing write/read of `project.json` from the `dev` path rather than leaving a misleading pointer. The explicit `<project_path>` argument is authoritative. Record that decision in the **tooling** project's own docs if/when this repo is itself initialized with bora; do not revive a per-consumer Architecture.md for it.

---

## 6. Validation and Guardrails

1. Hierarchical depth enforcement: reject `<path>` without a slash.
2. Collision safety: without `--force`, existing scaffold files (matched by role, including older dated briefing/Requirements names) are never silently overwritten.
3. Traversal safety: `.`/`..`/empty segments and absolute paths are rejected before any `Path` join.
4. Tag-count safety: if `--tags` is supplied, its element count must equal path depth; otherwise error.
5. Scope isolation: `lint` and `context`/`status` never read across project boundaries; cross-project `depends_on`/`parent` references are reported as errors.
6. `write` profile isolation: no changes to `bora write` commands or their file layout.
7. Help accuracy: `bora dev --help` and `bora dev init --help` reflect the new required `<project_path>` and `--tags`/`--force` options; removed commands do not appear; help text says `Status.md` not `Tasks.md`, and names the dated briefing/Requirements files.
8. Filename safety: discovery must not treat a Requirements file as the project briefing (the ` Requirements.md` suffix disambiguates).
9. Workflow accuracy: AGENTS.md and the skill template must state discuss-architecture → write Requirements → create tickets, that `Status.md` is generated by `bora dev status`, and that a ticket/subtask is not `done` (and not committed) until Commit criteria pass.

---

## 7. Implementation Phases

### Phase 1 — Path validation and project-dir resolution
- Add `parse_project_path` / `validate_project_path` and `project_dir` / `project_tickets_dir` / `project_file` / `requirements_file` / `status_file` resolvers, including dated-name discovery (§2.4).
- Unit tests for valid depths (2/3/4), quoted spaces, dated-name discovery (including not confusing briefing vs Requirements), and all reject cases (depth 1, empty, `//`, `.`/`..`, traversal).

### Phase 2 — Rewrite `bora dev init` for hierarchical scaffolding + tag-inferred frontmatter
- Change Click signature to require `<project_path>` and add `--tags` + `--force`.
- Wire resolvers; implement collision-by-role; generate per-project scaffold (dated project briefing with inferred frontmatter, dated Requirements placeholder, `Status.md`, `tickets/.gitkeep`).
- Remove skill-install variadic from `init`; update help text.

### Phase 3 — Scope `ticket`/`status`/`context`/`lint` to project path; remove `decision`
- Update all `dev` ticket subcommands and `status`, `context`, `lint` to require `<project_path>` and use project-scoped resolvers.
- `status.py` writes `Status.md`; `context.py` includes the dated briefing + Requirements + `Status.md`; `lint.py` `known_ids` is project-local.
- Remove `bora dev decision` from help (hidden stub with removal message is acceptable).
- Update tests to invoke commands with project paths.

### Phase 4 — Remove `bora dev project`; drop Architecture / Implementation Plan / Tasks.md
- Remove or stub `bora dev project` (hidden, with removal message naming 0.4.5).
- Add `REQUIREMENTS_MD_TEMPLATE`; remove use of `ARCHITECTURE_MD_TEMPLATE` and any Implementation Plan template from `dev init`.
- Clean up `dev_project.py` archiving helpers and `PROJECTS_DIR` / `project.json` active logic.

### Phase 5 — Update AGENTS.md, skill template, templates, and README

#### AGENTS.md
- Apply the edits in §4.4 (philosophy, briefing sequence with architecture discussion, scope guardrail, Requirements-then-tickets workflow, status/context/lint examples, removal of decision-command workflow, frontmatter path, validation, diagram, Status.md rule).
- Ensure `bora dev init <path>` does not overwrite an existing root `AGENTS.md` unless `--force` is given; template source is `bora/templates.py:AGENTS_MD`.

#### Skill template (`bora/skill.py`)
- Same workflow and command examples as AGENTS.md: hierarchical `<project_path>`, Requirements-driven tickets, `bora dev status <project_path>` regenerates `Status.md`.

#### Templates (`bora/templates.py`)
- Update `PROJECT_MD_TEMPLATE` frontmatter for hierarchy-inferred keys (`hierarchy` always; tag-mapped keys when `--tags` is present; `last_reviewed` / `focus`).
- Add `REQUIREMENTS_MD_TEMPLATE` with the sections in §4.3. Do not scaffold Architecture.md or Implementation Plan.md.
- Stop emitting `Tasks.md` as a name in templates and generated headers; the dashboard title/header should say Status.

#### README.md
Update the following sections to the hierarchical model; remove all flat `docs/ai/` singleton assumptions:

1. **Overview / How it works** — Describe `docs/ai/<Codebase>/<Target>/<Project>/(YYYY-MM-DD) {ProjectName}.md`, the sibling Requirements file, and `Status.md`. Note that multiple projects coexist under `docs/ai/`. Add a tree diagram identical to §2.1.
2. **Quick start (For developers)** — Replace `bora dev init` (no args) with `bora dev init <project_path> [--tags ...]` and show the QromaCore example both with and without tags, including quoted-space form: `bora dev init "QromaCore/Hamburg/Gallery Refactor" --tags Codebase,"Release Train",Project`. Describe the discuss-architecture → Requirements → tickets loop.
3. **Commands reference** — Update every `dev` command row to show the required `<project_path>` positional:
   - `bora dev ticket new <project_path> "<title>"`
   - `bora dev ticket list/show/set/note/subtask <project_path> ...`
   - `bora dev status <project_path>` → writes `Status.md`
   - `bora dev context <project_path> [--budget N]`
   - `bora dev lint <project_path>`
   Add a note that missing `<project_path>` is an error; there is no active-project fallback.
   Add a "Removed in 0.4.5" callout for `bora dev decision` (record decisions in the Requirements file).
4. **Remove deprecated docs** — Delete the `bora dev project` command section and any `docs/ai/Projects/` archival description; replace with a "Removed in 0.4.5" callout pointing to `bora dev init --tags` consolidation.
5. **Remove `specs` / Architecture.md / Implementation Plan.md / Tasks.md references** — Redirect to the dated Requirements file and `Status.md`. Document that Requirements is the per-project spec and ticket source.
6. **Conventions** — `Status.md` is per-project and regenerated by `bora dev status <path>`; `AGENTS.md` is root-only and contains the scope guardrail and the Requirements workflow; no migration for flat layouts.
7. **Help text parity** — Ensure `bora dev --help` and `bora dev init --help` strings match the README examples; update any stale command synopses in docstrings.

---

## 8. Deliverables

- Updated `bora/paths.py` with hierarchical resolvers, dated-file discovery, and validation.
- Updated `bora/cli.py` (`dev init` + all project-scoped `dev` commands, removal of `dev project`).
- Updated `bora/status.py` (writes `Status.md`), `bora/context.py`, `bora/lint.py`, `bora/ticket.py` / `bora/create.py` to use project-scoped paths.
- Updated `bora/templates.py` (`AGENTS_MD`, `PROJECT_MD_TEMPLATE`, new `REQUIREMENTS_MD_TEMPLATE`; no Architecture/Implementation Plan/Tasks.md scaffolding).
- Updated `bora/skill.py` skill template for the 0.4.5 workflow.
- Cleaned `bora/dev_project.py` / `paths.py` constants (`PROJECTS_DIR`, flat `TICKETS_DIR`, `TASKS_FILE`, etc.) as appropriate.
- Per-project scaffold: dated project briefing, dated Requirements placeholder, `Status.md`, `tickets/.gitkeep`.
- Updated root `AGENTS.md` template per §4.4.
- Updated `README.md` per Phase 5.
- Tests covering path validation, dated-name discovery, init happy/collision/quote/tag cases, `Status.md` generation, absence of `bora dev decision` from help, and project-scoped command behavior.
- `bora dev lint <project_path>` passes on all generated tickets; `bora dev --help` and `bora dev init --help` match README/AGENTS.md examples.

---

## 9. Non-goals

- No migration or backwards-compatibility shims for existing flat `docs/ai/Project.md` + `docs/ai/tickets/` layouts.
- No root `docs/ai/Status.md` or `docs/ai/Tasks.md` aggregation across projects.
- No global active-project tracking or `bora dev use` pointer.
- No changes to `bora write` profile.
- No `docs/ai/specs/` support for new hierarchical projects.
- No separate `Architecture.md` or `Implementation Plan.md` in new projects.
- No ticket-claim / multi-agent assignment CLI. Parallel agents are a workflow convention in AGENTS.md only.
- No `bora dev decision` command. Decisions are edited into the Requirements file.
