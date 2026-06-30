# Bora

> *Bora* — Brazilian Portuguese slang for *let's go*

**Bora is a CLI that keeps your AI collaborator oriented across sessions, models, and projects.**

Whether you're a developer building software with an AI coding agent, or a writer using AI to research and plan a manuscript, bora solves the same two problems:

1. **Context decay.** Every new AI chat starts from zero. You re-explain the project, often inconsistently, and details get lost.
2. **Model drift.** Switching between Claude, GPT, Gemini, or a local model means starting the briefing over.

Bora fixes this by maintaining a small, structured set of Markdown files inside your project. Any model — any tool — can read them to get oriented in seconds. The files travel with your project, stay in version control, and are always the authoritative source of what's happening and why.

Bora 0.3.0 ships two isolated **profiles**:

- **`dev`** — for software projects: tickets, architecture decisions, task dashboards, and AI tool skill integration.
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
- [Upgrading from 0.2.x](#upgrading-from-02x)
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
| `dev` | `bora dev init` | Software development |
| `write` | `bora write init` | Writing projects |

Bora enforces profile isolation: running a `dev` command in a `write` project (or vice versa) exits with a clear error. This keeps the two workflows from interfering with each other.

If you run a command in a project that has no profile yet (for example, a project created before 0.3.0), bora prompts you to choose one and writes the file before continuing.

---

## For developers

### How it works (dev)

`bora dev init` scaffolds four files and a directory:

```
AGENTS.md              ← AI agent instructions (entry point for any tool)
docs/ai/
  Project.md           ← what you're building and why
  Architecture.md      ← design decisions, component layout, decision log
  Tasks.md             ← auto-generated dashboard (never hand-edit)
  tickets/             ← one Markdown file per ticket
.bora/
  profile.json         ← profile lock (dev)
```

Each ticket is a Markdown file with YAML frontmatter for machine-readable state (`status`, `priority`, `depends_on`, `subtasks`) and a free-form body for human-readable context (description, acceptance criteria, notes). `Tasks.md` is regenerated from the tickets any time you run `bora dev status`.

An AI agent reads `AGENTS.md` first, which tells it how to use the rest. It can then run `bora dev ticket set`, `bora dev ticket note`, and `bora dev lint` directly — the whole loop works from inside a model's shell.

### Quick start (dev)

```bash
# Start in your project directory (existing or new)
cd /path/to/my-project

# Scaffold the project and install the bora skill for Claude Code
bora dev init claude

# Fill in what you're building
$EDITOR docs/ai/Project.md

# Create a ticket
bora dev ticket new "Implement login flow" --priority high

# Mark it in-progress (fuzzy ID match — no need to type the full ID)
bora dev ticket set 01 status in-progress

# Add a note as work progresses
bora dev ticket note 01 "Auth service wired up, still need session handling"

# Regenerate the task dashboard
bora dev status

# Brief a fresh model session (pipe to clipboard)
bora dev context | pbcopy
```

### Dev commands

#### Project initialisation

| Command | What it does |
|---------|-------------|
| `bora dev init [tool ...]` | Scaffold `AGENTS.md`, `docs/ai/`, tickets directory, and `.bora/profile.json`. Optionally install the bora skill for one or more AI tools in the same step: `bora dev init claude`, `bora dev init all`. Add `--force` to overwrite existing files. |

#### Tickets

| Command | What it does |
|---------|-------------|
| `bora dev ticket new "<title>"` | Create a new ticket. Options: `--type` (feature/bug/chore/spike), `--priority` (high/medium/low), `--parent <id>` (for child tickets), `--no-edit` (skip opening `$EDITOR`). |
| `bora dev ticket list` | List all tickets in a table. Filters: `--status`, `--type`, `--priority`, `--blocked`. |
| `bora dev ticket show <id>` | Print a ticket's full contents. Fuzzy ID match: `01` matches `20260628-01-my-ticket`. |
| `bora dev ticket set <id> <field> <value>` | Update a frontmatter field. Settable fields: `title`, `type`, `priority`, `status`, `notes`, `parent`. Setting `status done` auto-populates the closed date. |
| `bora dev ticket note <id> "<text>"` | Append a dated entry to a ticket's Notes section. Use this to record progress without rewriting the whole file. |
| `bora dev ticket subtask <id> <subtask-id> <status>` | Update a frontmatter subtask's status (todo/in-progress/done). |

#### Project state

| Command | What it does |
|---------|-------------|
| `bora dev status` | Regenerate `docs/ai/Tasks.md` from the current ticket state. |
| `bora dev context [--budget N]` | Print briefing content for a fresh model session — all the files an agent should read, in order. Pass `--budget <tokens>` to get a token-bounded version. |
| `bora dev lint` | Validate frontmatter and cross-references across all tickets. Run this after any model writes to a ticket file. |

#### Architecture decisions

| Command | What it does |
|---------|-------------|
| `bora dev decision new "<title>"` | Append a dated, templated decision entry to `Architecture.md` and open it in `$EDITOR`. |

#### AI tool skills

| Command | What it does |
|---------|-------------|
| `bora dev skill install <tool>` | Install the bora skill for an AI tool. Tools: `claude`, `opencode`, `all`. Default: user-level install (`~/.claude/`). Add `--project` to install inside the repo instead. |
| `bora dev skill uninstall <tool>` | Remove the bora skill. |
| `bora dev skill list` | Show where the bora skill is installed for each known tool. |

### AI tool skills

Claude Code, OpenCode, and other agentic tools support **skills** — directories containing a `SKILL.md` that the agent loads when its description matches the current task. Bora ships a skill that tells the agent how to use the CLI and maintain the `docs/ai/` files correctly.

Install as part of `bora dev init`:

```bash
bora dev init claude         # scaffold + skill for Claude Code
bora dev init claude opencode  # scaffold + both tools
bora dev init all            # scaffold + all known tools
```

Or install the skill on its own (after `bora dev init`):

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

The uninstall command only removes a `SKILL.md` whose frontmatter identifies it as bora's — it won't delete a skill it didn't create. Pass `--force` to override.

| Tool | User-level path | Project-level path |
|------|----------------|--------------------|
| `claude` | `~/.claude/skills/bora/SKILL.md` | `./.claude/skills/bora/SKILL.md` |
| `opencode` | `~/.config/opencode/skills/bora/SKILL.md` | `./.opencode/skills/bora/SKILL.md` |

### Dev conventions

- **Ticket IDs are generated, not chosen.** The format is `YYYYMMDD-NN-slug`. Never rename ticket files — the ID is the source of truth for `depends_on` and `parent` references.
- **`Tasks.md` is auto-generated.** Never hand-edit it. Update tickets and run `bora dev status`.
- **Subtasks live in two places by design.** Major subtasks appear in frontmatter (`subtasks:` list) — they're queryable and visible in `Tasks.md`. Small subtasks are Markdown checkboxes in the ticket body — they're counted but not individually tracked.
- **Decisions are append-only.** Add new entries to `Architecture.md`; don't rewrite old ones. History matters.
- **`AGENTS.md` is the entry point.** AI tools that support `AGENTS.md` (Claude Code, Cursor, others) load it automatically. It tells the agent what the project is, how to work, and what commands to use.

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

For dev projects, run `bora dev context --budget <N>` and paste the output as your first message. The model gets the same complete briefing every time.

For write projects, run `bora write status` and paste the output. Ask the model to generate a `Summary.md` and save its response.

**Agentic tools with file access** (Claude Code, Cursor, Aider, etc.)

The model reads `AGENTS.md` and follows its instructions to discover the rest. For dev projects, the agent can run `bora dev ticket set`, `bora dev lint`, and `bora dev status` directly from its shell as work progresses.

**Local models**

The same flows work with local models. Smaller models (under ~14B parameters) may occasionally produce malformed YAML frontmatter in ticket or planning files. Run `bora dev lint` after any model writes to a ticket file to catch these early.

---

## Upgrading from 0.2.x

Bora 0.3.0 moves all commands under `bora dev` or `bora write`. The old top-level `bora init` prints a deprecation warning and exits without doing anything.

To migrate an existing project:

1. Upgrade bora:
   ```bash
   pipx upgrade bora
   ```

2. Add a profile file. Run any `bora dev` command and choose `dev` at the prompt — bora writes the file automatically. Or create it manually:
   ```bash
   mkdir -p .bora
   cat > .bora/profile.json << 'EOF'
   {
     "version": "0.3.0",
     "profile": "dev",
     "initialized_at": "2026-06-28T00:00:00+00:00",
     "config": { "auto_archive": true, "research_log_mode": "full_interaction" }
   }
   EOF
   ```

3. That's it. All existing tickets, `docs/ai/` files, and `AGENTS.md` are untouched. Commands that used to be `bora ticket ...` are now `bora dev ticket ...`.

---

## Contributing

The source is in `bora/`. Here's what each module does:

| File | Purpose |
|------|---------|
| `cli.py` | Click command surface — `dev` and `write` subgroups, profile-aware help filtering |
| `profile.py` | `.bora/profile.json` read/write/lock, upgrade prompt |
| `paths.py` | Repo-root detection and shared path constants |
| `templates.py` | All scaffolded file templates (dev and write) |
| `ticket.py` | Frontmatter parsing, fuzzy ID matching, body progress tracking |
| `create.py` | Chronological ticket ID generation |
| `lint.py` | Frontmatter validation rules |
| `status.py` | `Tasks.md` generation |
| `context.py` | Briefing assembly with optional token budget |
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
bora dev init
bora dev ticket new "Test ticket" --priority high --no-edit
bora dev ticket set 01 status in-progress
bora dev status
bora dev lint
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
