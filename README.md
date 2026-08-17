# Bora

> *Bora* — Brazilian Portuguese slang for *let's go*

**Bora is a CLI that keeps your AI collaborator oriented across sessions, models, and projects.**

Whether you're a developer building software with an AI coding agent, or a writer using AI to research and plan a manuscript, bora solves the same two problems:

1. **Context decay.** Every new AI chat starts from zero. You re-explain the project, often inconsistently, and details get lost.
2. **Model drift.** Switching between Claude, GPT, Gemini, or a local model means starting the briefing over.

Bora fixes this by maintaining a small, structured set of Markdown files inside your project. Any model — any tool — can read them to get oriented in seconds. The files travel with your project, stay in version control, and are always the authoritative source of what's happening and why.

Bora 0.7.0 ships two isolated **profiles**:

- **`dev`** — for software projects: hierarchical tickets, a dated Requirements spec, implementation plans on each ticket, a ten-skill pack (`bora`, `bora-plan`, `bora-tdd`, `bora-execute`, `bora-design`, `bora-worktree`, `bora-review`, `bora-debug`, `bora-verify`, `bora-finish`), and per-project status dashboards.
- **`write`** — for writing projects: chapter scaffolding, research interaction logs, story context, and summary generation.

---

## Contents

- [Installation](#installation)
- [Profiles](#profiles)
- [For developers](#for-developers)
  - [How it works](#how-it-works-dev)
  - [Quick start](#quick-start-dev)
  - [Commands](#dev-commands)
  - [AI tool skills](#ai-tool-skills)
  - [Conventions](#dev-conventions)
- [For writers](#for-writers)
  - [How it works](#how-it-works-write)
  - [Quick start](#quick-start-write)
  - [Commands](#write-commands)
  - [Obsidian integration](#obsidian-integration)
  - [Conventions](#write-conventions)
- [Working across models](#working-across-models)
- [Optional model routing](#optional-model-routing)
- [Upgrading](#upgrading)
- [Contributing](#contributing)

---

## Installation

The recommended way to install Python CLIs globally is **pipx**, which gives `bora` its own isolated environment and puts it on your `PATH` without touching your system Python.

### Install pipx (if you don't have it)

```bash
# macOS
brew install pipx
pipx ensurepath

# Linux / WSL
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Windows (PowerShell)
python -m pip install --user pipx
python -m pipx ensurepath
```

After running `pipx ensurepath`, open a new terminal so the updated `PATH` takes effect.

### Install bora

```bash
# From PyPI (once published):
pipx install bora

# From GitHub:
pipx install git+https://github.com/tonyknight/Bora.git
```

Verify the install:

```bash
bora --version
```

### Upgrade

```bash
pipx upgrade bora
```

Upgrading the CLI does **not** change files in an existing repo. In each project, run `bora dev upgrade` so `AGENTS.md` and the installed skill pack match this version. See [Upgrading](#upgrading).

### Uninstall

```bash
pipx uninstall bora
```

### Alternative: pip --user

If you prefer not to use pipx:

```bash
pip install --user bora
```

If `bora` isn't found after install, your user binary directory (`~/.local/bin` on Linux/macOS) may not be on your `PATH`. Add it:

```bash
# ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"
```

### Development install (from source)

```bash
git clone https://github.com/tonyknight/Bora.git
cd Bora
pipx install -e .
```

Changes to the source take effect immediately — no reinstall needed.

---

## Profiles

Every bora project has a **profile** stored in `.bora/profile.json`. The profile determines which commands are available and which appear in `--help`.

| Profile | Initialise with | Designed for |
|---------|----------------|-------------|
| `dev` | `bora dev init <project_path>` | Software development |
| `write` | `bora write init` | Writing projects |

Bora enforces profile isolation: running a `dev` command in a `write` project (or vice versa) exits with a clear error. This keeps the two workflows from interfering with each other.

If you run a command in a project that has no profile yet (for example, a project created before 0.3.0), bora prompts you to choose one and writes the file before continuing.

---

## For developers

### How it works (dev)

`bora dev init <project_path>` scaffolds one project under a hierarchical path. Multiple projects may coexist under `docs/ai/`. There is no active-project pointer — every command takes an explicit `<project_path>`.

Example: `bora dev init "QromaCore/Hamburg/Gallery Refactor"` on 2026-08-14 yields:

```
AGENTS.md              ← AI agent instructions (repo root only)
docs/
  ai/
    QromaCore/
      Hamburg/
        Gallery Refactor/
          (2026-08-14) Gallery Refactor.md              ← project briefing
          (2026-08-14) Gallery Refactor Requirements.md ← architecture + spec
          Status.md                                     ← auto-generated dashboard
          tickets/
            .gitkeep
.bora/
  profile.json         ← profile lock (dev)
```

Deeper paths are valid too: `bora dev init Acme/Platform/Auth/OAuth Refresh` (depth 4). `{ProjectName}` is the last segment.

The dated briefing describes **what** is being built and **why**. After the human and agent discuss architecture, they fill the sibling Requirements file — that document is the per-project spec and the source of tickets (from its Tasks Breakdown). Each ticket holds its own `## Implementation plan` (`T01`, `T02`, …); Requirements is not a commit script. `Status.md` is regenerated from that project's tickets any time you run `bora dev status <project_path>`. Never hand-edit it.

After Requirements are approved, say **go**. The agent creates tickets, loads `bora-execute`, and walks the **whole board**. After each ticket it shows completed vs remaining. You should not need to type `bora dev` again until you want a PR. Merge and PR stay your git.

Each ticket is a Markdown file under `docs/ai/<path>/tickets/` with YAML frontmatter for machine-readable state (`status`, `priority`, `depends_on`, `subtasks`, `plan_status`, `current_task`) and a free-form body for human-readable context (description, acceptance criteria, implementation plan, notes). Ticket IDs are unique per-project, not repo-global.

An AI agent reads root `AGENTS.md` first (scope guardrail and Requirements workflow), then the human-referenced project briefing. It runs `bora dev ticket …`, `bora dev plan …`, `bora dev lint`, and `bora dev status` itself — you run `init`, `skill install`, and `upgrade`.

### Quick start (dev)

First-time on a machine, then once per project. Example: add a Share Extension to an existing photo app.

```bash
# Once on the machine
pipx install bora
bora dev skill install all          # or claude / opencode — required

# Once per new Bora project (the only project command you must type)
cd ~/src/PhotoApp
bora dev init "PhotoApp/iOS/Share Extension" --tags Codebase,Target,Project

# Write what/why in the dated briefing (not Requirements, not a ticket)
$EDITOR "docs/ai/PhotoApp/iOS/Share Extension/(YYYY-MM-DD) Share Extension.md"
```

Then start an agent session and point it at that briefing:

> Work in `docs/ai/PhotoApp/iOS/Share Extension`. Discuss architecture with me before filling Requirements. Do not create tickets yet.

After you approve Requirements, say **go**. The agent creates tickets from the Tasks Breakdown, writes an implementation plan on each ticket, and walks the board with TDD. You watch commits of the form `{ticket-id} T01: …`. Merge/PR is still your git.

Skill install is required. Without it you have Markdown; you do not have `bora-plan` / `bora-tdd` / `bora-execute`.

Missing `<project_path>` is an error. There is no active-project fallback. Chat-only models (no shell): `bora dev context "PhotoApp/iOS/Share Extension"` and paste — execute quality is weaker.

Ticket, plan, lint, and status commands are **agent API**. You do not need to type them on the happy path. For reference:

```bash
bora dev ticket new "PhotoApp/iOS/Share Extension" "Add Share Extension target" --priority high
bora dev plan show "PhotoApp/iOS/Share Extension" 01
bora dev status "PhotoApp/iOS/Share Extension"
bora dev context "PhotoApp/iOS/Share Extension" | pbcopy
```

### Dev commands

#### Project initialisation

| Command | What it does |
|---------|-------------|
| `bora dev init <project_path> [--tags …] [--force]` | Scaffold a dated project briefing, dated Requirements file, `Status.md`, and `tickets/` under `docs/ai/<project_path>/`. Writes root `AGENTS.md` only if it is missing (use `--force` to overwrite it). `--tags` is a CSV of labels matching path segments, for example `--tags Codebase,"Release Train",Project`. Do **not** use `--force` to upgrade an existing repo — use `bora dev upgrade`. |

##### Removed in 0.4.5

- **`bora dev project`** — versioning and `docs/ai/Projects/` archival are gone. Hierarchy and optional tags are set at init: `bora dev init <project_path> --tags …`.
- **`bora dev decision`** — record decisions in the project's Requirements file (typically under Architecture or Open questions).

#### Tickets

Every ticket command requires `<project_path>` first. Missing it is an error.

| Command | What it does |
|---------|-------------|
| `bora dev ticket new <project_path> "<title>"` | Create a new ticket. Options: `--type` (feature/bug/chore/spike), `--priority` (high/medium/low), `--parent <id>` (for child tickets), `--no-edit` (skip opening `$EDITOR`). |
| `bora dev ticket list <project_path>` | List tickets in that project. Filters: `--status`, `--type`, `--priority`, `--blocked`. |
| `bora dev ticket show <project_path> <id>` | Print a ticket's full contents. Fuzzy ID match: `01` matches `20260628-01-my-ticket`. |
| `bora dev ticket set <project_path> <id> <field> <value>` | Update a frontmatter field. Settable fields: `title`, `type`, `priority`, `status`, `notes`, `parent`. Setting `status done` auto-populates the closed date. |
| `bora dev ticket note <project_path> <id> "<text>"` | Append a dated entry to a ticket's Notes section. Use this to record progress without rewriting the whole file. |
| `bora dev ticket subtask <project_path> <id> <subtask-id> <status>` | Update a frontmatter subtask's status (todo/in-progress/done). |

#### Implementation plans

Plans live **on the ticket** (`## Implementation plan`), not in Requirements and not in a `plans/` folder. There is no `bora dev plan new` and no `bora dev execute` — “go” in chat starts `bora-execute`.

| Command | What it does |
|---------|-------------|
| `bora dev plan show <project_path> <id>` | Print a ticket's `## Implementation plan` section. |
| `bora dev plan set <project_path> <id> status <value>` | Set plan status: `draft`, `approved`, `in-progress`, `done`, `blocked`. `in-progress` also sets the ticket in-progress if it was `todo`. `blocked` sets the ticket `blocked`. `done` does **not** close the ticket. |
| `bora dev plan set <project_path> <id> current_task <Tnn>` | Set the current plan task id. |
| `bora dev plan task <project_path> <id> <Tnn> todo\|done` | Check or uncheck a plan task. Advances `current_task` to the next open `Tnn`. |

#### Project state

| Command | What it does |
|---------|-------------|
| `bora dev status <project_path>` | Regenerate that project's `Status.md` from its ticket state. |
| `bora dev context <project_path> [--budget N]` | Print briefing content for a fresh model session — root `AGENTS.md` plus that project's dated briefing, Requirements, `Status.md`, and in-progress/blocked tickets. Pass `--budget <tokens>` to get a token-bounded version. |
| `bora dev lint <project_path>` | Validate frontmatter and cross-references across that project's tickets. Run this after any model writes to a ticket file. |
| `bora dev routing show <project_path>` | Print the effective model-tier routing configuration. Informational only; does not contact a router. |
| `bora dev upgrade [--dry-run] [--agents-only] [--skills-only] [--force]` | Refresh the managed region of root `AGENTS.md` and rewrite already-installed skill packs to match this CLI. Does not touch project briefings, Requirements, or tickets. See [Upgrading](#upgrading). |

#### AI tool skills

| Command | What it does |
|---------|-------------|
| `bora dev skill install <tool>` | Install the bora **skill pack** (ten skills) for an AI tool. Tools: `claude`, `opencode`, `cursor`, `all`. Default: user-level install. Add `--project` to install inside the repo instead. |
| `bora dev skill uninstall <tool>` | Remove the bora skill pack. |
| `bora dev skill list` | Show where the bora skill pack is installed for each known tool. |

### AI tool skills

Claude Code, OpenCode, Cursor, and other agentic tools support **skills** — directories containing a `SKILL.md` that the agent loads when its description matches the current task. Bora 0.7.0 ships a **pack** of ten skills:

| Skill | When it loads |
|-------|----------------|
| `bora` | Session start in a bora project (briefing, tickets, `AGENTS.md`) |
| `bora-design` | Architecture conversation before Requirements are approved |
| `bora-plan` | A ticket needs `## Implementation plan` before code |
| `bora-tdd` | Implementing a plan task (failing test → code → verify → commit) |
| `bora-execute` | Requirements approved and you say **go** / implement / resume the board |
| `bora-worktree` | Start of execute — optional git isolation; records `origin_branch` |
| `bora-verify` | Before claiming task/ticket/board complete or finish |
| `bora-review` | After a ticket's last commit, before marking `done` |
| `bora-debug` | Unexpected verify/build failure (not expected RED) |
| `bora-finish` | Board complete — merge to `origin_branch`, PR, or keep; optional worktree cleanup |

Install the pack after `bora dev init <project_path>`:

```bash
# User-level — available in every project
bora dev skill install claude
bora dev skill install all

# Project-level — ships inside this repo
bora dev skill install claude --project
```

Show what's installed where:

```bash
bora dev skill list
```

Remove:

```bash
bora dev skill uninstall claude          # user-level
bora dev skill uninstall claude --project  # this repo only
```

The uninstall command only removes directories whose `SKILL.md` declares a bora-owned name (`bora`, `bora-plan`, `bora-tdd`, `bora-execute`). Pass `--force` to override.

| Tool | User-level path | Project-level path |
|------|----------------|--------------------|
| `claude` | `~/.claude/skills/bora/SKILL.md` (plus `bora-plan`, `bora-tdd`, `bora-execute`) | `./.claude/skills/bora/SKILL.md` (same pack) |
| `opencode` | `~/.config/opencode/skills/bora/SKILL.md` (plus the rest of the pack) | `./.opencode/skills/bora/SKILL.md` (same pack) |

### Dev conventions

- **Ticket IDs are generated, not chosen.** The format is `YYYYMMDD-NN-slug`. Never rename ticket files — the ID is the source of truth for `depends_on` and `parent` references. IDs are unique per-project, not repo-global.
- **`Status.md` is per-project and auto-generated.** Never hand-edit it. Update tickets and run `bora dev status <project_path>`. There is no root `docs/ai/Status.md` aggregation. After each ticket, `bora-execute` shows these buckets in chat (completed vs remaining) and continues — it does not ask whether to go on.
- **Implementation plans live on the ticket.** `## Implementation plan` with `T01`…`Tn` is the commit script. Do not put it in Requirements or a `plans/` folder.
- **Commit criteria gate done work and git commits.** Before marking a ticket or plan task `done`, and before any git commit, satisfy the **Commit criteria** section of that project's Requirements file: the plan task's Verify command passed (RED then GREEN), the change meets the requirement, and build/tests pass (including platform builds such as macOS/iOS when that is the target). Commit message format: `{ticket-id} {task-id}: {title}` (for example `20260814-01-add-target T01: add Share Extension target`). One commit per plan task. Bora does not create git commits; this is agent workflow. Resume with `git log --grep=<ticket-id>`.
- **`AGENTS.md` is root-only.** It contains the scope guardrail, skill-check gates, and the discuss-architecture → write Requirements → “go” → execute-the-board workflow. `init` writes it once (not overwritten unless you pass `--force`). Existing repos catch up with **`bora dev upgrade`**, which refreshes the managed region and preserves **Project-specific instructions**.
- **Subtasks live in two places by design.** Major subtasks appear in frontmatter (`subtasks:` list) — they're queryable and visible in `Status.md`. Small subtasks are Markdown checkboxes in the ticket body — they're counted but not individually tracked. Plan tasks (`T01`…) are the commit script; they are not the same as frontmatter subtasks.
- **Decisions live in the Requirements file.** After agreeing with the human, edit Architecture or Open questions in the dated Requirements file. There is no decision command.
- **No migration for flat layouts.** Hierarchical `docs/ai/<path>/` projects are the layout since 0.4.5. New work does not convert `docs/ai/Project.md` trees.

---

## For writers

### How it works (write)

`bora write init` scaffolds a writing project:

```
AGENTS.md              ← AI agent instructions (role, boundaries, workflow rules)
doc/ai/
  Project.md           ← story overview: premise, plot, characters, worldbuilding
Summary.md             ← latest AI-generated context briefing (ephemeral)
Summary/               ← archive of previous summaries
.bora/
  profile.json         ← profile lock (write)
```

As you create chapters, bora adds:

```
Chapters/
  Chapter 001 - The Arrival/
    001 - The Arrival.md       ← manuscript (author-only, agents never write here)
    001 - ChapterProject.md    ← planning: beats, arcs, pacing, agent notes
    001 - Research.md          ← research log: AI interactions, sources, verification
```

The core workflow is:

1. **Write** your chapter notes and research questions in `ChapterProject.md`.
2. **Ask your AI** to research topics. The agent logs interactions in `Research.md`.
3. **Run `bora write status`** to compile everything into a structured briefing.
4. **Paste the briefing** into a new chat with your AI. Ask it to generate an updated `Summary.md`.
5. **Save the response** as `Summary.md`. Next time you run `bora write status`, it's archived and a fresh one is generated.

The AI never touches your manuscript. The creative work stays yours.

### Quick start (write)

```bash
# Create and enter your project directory
mkdir my-novel && cd my-novel

# Scaffold the write project
bora write init

# Set up your story context
$EDITOR AGENTS.md              # tell your AI its role and boundaries for this story
$EDITOR doc/ai/Project.md      # add your premise, characters, plot structure

# Create your first chapter
bora write chapter "The Arrival"

# Fill in the chapter plan
$EDITOR "Chapters/Chapter 001 - The Arrival/001 - The Arrival ChapterProject.md"

# Add a second chapter
bora write chapter "The Conflict"

# Compile a briefing for your AI model
bora write status

# Paste the output into Claude / ChatGPT / your model of choice
# Ask: "Based on this project context, generate an updated Summary.md"
# Save the response as Summary.md
```

### Write commands

#### Project initialisation

| Command | What it does |
|---------|-------------|
| `bora write init` | Scaffold `AGENTS.md`, `doc/ai/Project.md`, `Summary.md`, `Summary/`, and `.bora/profile.json`. Does not create chapter directories (use `bora write chapter` for that). Add `--force` to overwrite existing files. |

#### Chapters

| Command | What it does |
|---------|-------------|
| `bora write chapter "<name>"` | Create the next chapter directory under `Chapters/`. The ID is 3-digit zero-padded and auto-increments by scanning existing chapter directories (`001`, `002`, ...). Creates three files: an empty manuscript, a `ChapterProject.md` planning template, and a `Research.md` log. |

#### Project status

| Command | What it does |
|---------|-------------|
| `bora write status` | Read `Project.md`, all `ChapterProject.md` files, and all `Research.md` files. Compute approximate word counts, chapter status counts, and research topic frequency. Archive the existing `Summary.md` to `Summary/YYYY-MM-DD - Summary.md` (collision-safe). Print a structured briefing to stdout. |

#### Skills

| Command | What it does |
|---------|-------------|
| `bora write skill install obsidian` | Install a vault-aware agent prompt to `.obsidian/plugins/bora-writer/` (`SKILL.md`, `manifest.json`, `README.md`). Add `--force` to overwrite. |
| `bora write skill uninstall obsidian` | Remove the `.obsidian/plugins/bora-writer/` directory. Add `--force` if `SKILL.md` is missing. |

### Obsidian integration

If you use [Obsidian](https://obsidian.md) as your writing environment, bora can install a vault-aware prompt that orients your AI to the project's structure:

```bash
bora write skill install obsidian
```

This creates `.obsidian/plugins/bora-writer/` with:

- **`SKILL.md`** — a prompt template describing the vault structure, the chapter layout, the `Research.md` format, and the rule that agents never write to manuscript files. Paste its contents into your AI model's system prompt or context window.
- **`manifest.json`** — Obsidian community plugin metadata.
- **`README.md`** — setup instructions.

To remove it:

```bash
bora write skill uninstall obsidian
```

### Write conventions

- **Agents never write to manuscript files.** The `001 - Chapter Name.md` files are author-only. If an agent modifies one, treat that as a mistake — the `AGENTS.md` template instructs it not to.
- **`Research.md` is a mixed Markdown/YAML log.** Each topic section has a small YAML block (`topic`, `date`, `agent`, `word_count`, `verified`) followed by the free-form interaction. The YAML lets you track what's been verified and by whom.
- **`Summary.md` is ephemeral.** Every `bora write status` run archives it. Don't invest in maintaining it by hand — that's the AI's job.
- **`ChapterProject.md` drives the briefing.** The `status` field (`draft`, `in-progress`, `completed`) and `target_words` feed the compiled status output. Keep them up to date.
- **Chapter IDs are calculated, not counted.** Deleting a chapter directory doesn't reset the counter — the next chapter always gets `max(existing IDs) + 1`. You won't accidentally reuse an ID.

---

## Working across models

Bora is model-agnostic. It produces plain Markdown and YAML that any LLM can read.

**Chat-only models** (web Claude, ChatGPT, Gemini, etc.)

For dev projects, run `bora dev context <project_path> --budget <N>` and paste the output as your first message. The model gets the same complete briefing every time.

For write projects, run `bora write status` and paste the output. Ask the model to generate a `Summary.md` and save its response.

**Agentic tools with file access** (Claude Code, Cursor, Aider, etc.)

The model reads `AGENTS.md` and follows its instructions to discover the rest. For dev projects, install the skill pack so `bora-execute` can walk the board after you say go. The agent runs `bora dev ticket …`, `bora dev plan …`, `bora dev lint`, and `bora dev status` from its shell.

**Local models**

The same flows work with local models. Smaller models (under ~14B parameters) may occasionally produce malformed YAML frontmatter in ticket or planning files. Run `bora dev lint <project_path>` after any model writes to a ticket file to catch these early.

---

## Optional model routing

This is an **advanced, optional** feature. You can ignore it unless you already use a model router. It is not part of [Quick start](#quick-start-dev).

Bora does not choose models. Bora identifies the relative reasoning requirements of its workflows and optionally communicates those requirements to compatible routing systems.

Installed skills declare a provider-neutral `model_tier` (`premium`, `standard`, `economy`, or `local`). Hosts that do not understand the field ignore it. Bora never embeds provider model names such as a specific Claude or GPT snapshot.

Users who want routing add `.bora/models.yaml` themselves. `bora dev init` and `bora dev upgrade` never create this file.

```yaml
routing:
  enabled: true
  tiers:
    premium: auto/smart
    standard: auto/coding
    economy: auto/cheap
    local: auto/offline
  skills:
    bora-review: economy
```

Values under `tiers` are opaque routing identifiers for your router (for example an OmniRoute alias). Bora does not interpret them as commercial model names. The optional `skills` map overrides the default tier for a pack skill without editing installed `SKILL.md` files.

`bora dev routing show <project_path>` prints the effective configuration. It is informational and does not contact a router. Missing `models.yaml` is not an error: status is `disabled` and default tiers are still listed.

OmniRoute is one example consumer: map Bora's `premium` / `standard` / `economy` / `local` hints to that system's routes. Any compatible router can do the same. Fallback policy, pricing, and provider selection stay in the router.

---

## Upgrading

### From 0.6.0 to 0.7.0

After `pipx upgrade bora`, run `bora dev upgrade` in each repo. That refreshes `AGENTS.md` to the 0.7.0 managed template and rewrites any already-installed skill pack with `model_tier` frontmatter. It does **not** create `.bora/models.yaml` and does not touch project briefings, Requirements, or tickets. Existing 0.6.x projects remain valid without a routing file.

### From 0.5.5 to 0.6.0

After `pipx upgrade bora`, run `bora dev upgrade` in each repo. That refreshes `AGENTS.md` to the 0.6.0 managed template and rewrites any already-installed skill pack. Project briefings, Requirements, and tickets are untouched.

### From 0.5.0 to 0.5.5

After `pipx upgrade bora`, run `bora dev upgrade` in each repo. That refreshes `AGENTS.md` to the 0.5.5 managed template (design, worktree, review, debug, verify, finish) and rewrites any already-installed ten-skill pack. Project briefings, Requirements, and tickets are untouched.

### From 0.4.5 to 0.5.0

Installing a new CLI does **not** by itself change files in the repo. After `pipx upgrade bora` (or equivalent), in each existing project:

```bash
bora dev upgrade
```

That command refreshes the managed region of `AGENTS.md` (so agents pick up plan-on-ticket, execute-the-board, and the new commit format) and rewrites any already-installed skill pack. It does not touch project briefings, Requirements, or tickets. Review `git diff AGENTS.md` and keep local rules under **Project-specific instructions**.

Do **not** use `bora dev init --force` as an upgrade path — that overwrites project scaffold files.

Existing 0.4.5 projects keep working without upgrade (old `AGENTS.md`, tickets with no plan section). New tickets from `ticket new` include an empty `## Implementation plan`.

### From 0.3.x to 0.4.5

0.4.5 replaces the flat `docs/ai/Project.md` layout with hierarchical `docs/ai/<Codebase>/<Target>/<Project>/` projects. Every `dev` command takes an explicit `<project_path>`. There is no active-project pointer and no `bora dev project` / `bora dev decision` command.

New work: `bora dev init <project_path> [--tags …]`. That creates a dated briefing, a dated Requirements file, per-project `Status.md`, and `tickets/`. There is no migration for existing flat trees — start a new hierarchical project alongside them if you still have the old files.

### From 0.3.x to 0.3.5

0.3.5 added `.bora/project.json` to track the active project file. That pointer is unused in 0.4.5 hierarchical projects; `<project_path>` is authoritative.

Summary archives are named `(YYYY-MM-DD) Summary.md` instead of `YYYY-MM-DD - Summary.md`. Existing archives are not renamed.

### From 0.2.x to 0.3.x

Bora 0.3.0 moved all commands under `bora dev` or `bora write`. The old top-level `bora init` prints a deprecation warning and exits.

1. Upgrade bora:
   ```bash
   pipx upgrade bora
   ```

2. Add a profile file. Run any `bora dev` command and choose `dev` at the prompt — bora writes the file automatically. Or create it manually:
   ```bash
   mkdir -p .bora
   cat > .bora/profile.json << 'EOF'
   {
     "version": "0.3.5",
     "profile": "dev",
     "initialized_at": "2026-01-01T00:00:00+00:00",
     "config": { "auto_archive": true, "research_log_mode": "full_interaction" }
   }
   EOF
   ```

3. All existing tickets, `docs/ai/` files, and `AGENTS.md` are untouched. Commands that used to be `bora ticket ...` are now `bora dev ticket ...`.

---

## Contributing

The source is in `bora/`. Here's what each module does:

| File | Purpose |
|------|---------|
| `cli.py` | Click command surface — `dev` and `write` subgroups, profile-aware help filtering |
| `profile.py` | `.bora/profile.json` read/write/lock, upgrade prompt |
| `paths.py` | Repo-root detection, hierarchical project-path validation, and resolvers |
| `templates.py` | All scaffolded file templates (dev and write) |
| `ticket.py` | Frontmatter parsing, fuzzy ID matching, body progress tracking |
| `create.py` | Chronological ticket ID generation |
| `lint.py` | Frontmatter validation rules |
| `status.py` | Per-project `Status.md` generation |
| `context.py` | Project-scoped briefing assembly with optional token budget |
| `skill.py` | Dev `SKILL.md` template and per-tool install/uninstall |
| `writer_init.py` | `bora write init` scaffolding |
| `writer_chapter.py` | `bora write chapter` scaffolding and ID calculation |
| `writer_status.py` | `bora write status` context compiler and Summary archival |
| `writer_skill.py` | `bora write skill install/uninstall obsidian` |

Tests live in `tests/`, one file per phase. Run them with:

```bash
python -m pytest tests/ -v
```

To manually smoke-test a dev project:

```bash
mkdir /tmp/test-bora && cd /tmp/test-bora && git init
bora dev init Acme/App
bora dev ticket new Acme/App "Test ticket" --priority high --no-edit
bora dev ticket set Acme/App 01 status in-progress
bora dev status Acme/App
bora dev lint Acme/App
```

To smoke-test a write project:

```bash
mkdir /tmp/test-write && cd /tmp/test-write
bora write init
bora write chapter "First Chapter"
bora write chapter "Second Chapter"
bora write status
```

---

## License

MIT.
