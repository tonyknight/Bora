# Bora

> *Bora* — Brazilian Portuguese slang for *let's go*

**Bora keeps your AI collaborator oriented across sessions, models, and projects — using Markdown that lives in git.**

A new chat starts from zero. Switching models starts the briefing over. Bora fixes both by putting the project’s source of truth in the repo: what you’re building, the spec, the tickets, and the commit-sized plan for each ticket. Any model that can read files can pick up where the last one left off.

Bora 0.7.5 has two profiles:

| Profile | For | You type | The agent runs |
| --- | --- | --- | --- |
| **`dev`** | Software | `init`, `skill install`, `upgrade`, and **go** in chat | Tickets, plans, lint, status, TDD, review |
| **`write`** | Manuscripts | `init`, `chapter`, `status` | Research logs and briefings — never the manuscript |

---

## Capabilities (dev)

**Project-level planning in git.** Each software effort is a directory under `docs/ai/<Codebase>/<Target>/<Project>/`. The briefing, Requirements, tickets, and per-ticket implementation plans are ordinary Markdown + YAML. They diff, branch, and review like code. There is no `plans/` folder and no cloud board: the plan for a ticket is a `## Implementation plan` section on that ticket (`T01`, `T02`, …).

**A defined workflow cycle.** Human and agent agree architecture, then write Requirements. You say **go**. The agent creates tickets from the Tasks Breakdown, plans each ticket, implements with TDD, verifies, reviews, and continues until the board is empty. You watch commits of the form `{ticket-id} T01: …`. Merge and PR stay your git.

**Optional model routing.** Skills declare a provider-neutral `model_tier`. A repo catalog can list fallback aliases per tier; a Bora project may opt in so each session fuzzy-matches those aliases to models **this** host can run. Bora does not choose models. Skip this unless you want cost-efficiency routing.

**Skills for agentic tools.** Claude Code, Cursor, and OpenCode get a ten-skill pack (`bora-design` → `bora-execute` → `bora-tdd` → `bora-finish`). Install user-level or **`--project`** so the pack is committed with the repo.

---

## Contents

- [Install](#install)
- [Quick start (dev)](#quick-start-dev)
- [Workflow cycle](#workflow-cycle)
- [What’s in the repo](#whats-in-the-repo)
- [Commands](#dev-commands)
- [Skills](#ai-tool-skills)
- [Optional model routing](#optional-model-routing)
- [Writers](#for-writers)
- [Upgrading](#upgrading)
- [Contributing](#contributing)

---

## Install

```bash
# pipx (recommended)
brew install pipx && pipx ensurepath    # macOS; then open a new terminal
pipx install git+https://github.com/tonyknight/Bora.git
bora --version

# Later
pipx upgrade bora                       # CLI only — then in each repo:
bora dev upgrade                        # refresh AGENTS.md + installed skills
```

`pip install --user bora` works if `~/.local/bin` is on `PATH`. From a clone: `pipx install -e .`

Every repo has a profile in `.bora/profile.json` (`dev` or `write`). Commands from the other profile exit with an error.

---

## Quick start (dev)

Once on the machine, once per project. Example: a Share Extension in an existing photo app.

```bash
pipx install git+https://github.com/tonyknight/Bora.git
bora dev skill install all              # or claude / cursor / opencode
                                        # add --project to commit skills in this repo

cd ~/src/PhotoApp
bora dev init "PhotoApp/iOS/Share Extension" --tags Codebase,Target,Project
```

Edit the dated briefing (what/why — not Requirements yet):

```bash
$EDITOR "docs/ai/PhotoApp/iOS/Share Extension/(YYYY-MM-DD) Share Extension.md"
```

In a new agent session:

> Work in `docs/ai/PhotoApp/iOS/Share Extension`. Discuss architecture with me before filling Requirements. Do not create tickets yet.

Approve Requirements, then say **go**. The agent walks the board. Skill install is required for that cycle; without it you have Markdown only.

You type `init`, `skill install`, and `upgrade`. Ticket, plan, lint, and status are **agent API** (`bora dev ticket …` still works if you need them). Chat-only models: `bora dev context "PhotoApp/iOS/Share Extension"` and paste.

---

## Workflow cycle

```text
Briefing (what / why)
    → discuss architecture
        → Requirements (spec, tests, commit criteria, Tasks Breakdown)
            → you say go
                → tickets (from the breakdown)
                    → plan on the ticket (T01…)
                        → TDD → verify → review → next ticket
                            → board empty → finish (merge / PR / keep)
```

Gates: no tickets until Requirements are approved; no production code until that ticket has an implementation plan; no `done` without the Requirements **Commit criteria**. After go, the agent does not ask whether to continue.

`bora-execute` may isolate work in a git worktree and record `origin_branch` on the briefing. Finish merges only to that branch.

---

## What’s in the repo

`bora dev init "QromaCore/Hamburg/Gallery Refactor"` creates:

```text
AGENTS.md                          ← agent instructions (repo root, once)
.bora/profile.json                 ← profile lock (dev)
docs/ai/QromaCore/Hamburg/Gallery Refactor/
  (YYYY-MM-DD) Gallery Refactor.md
  (YYYY-MM-DD) Gallery Refactor Requirements.md
  Status.md                        ← generated; never hand-edit
  tickets/
```

Multiple projects can share one repo. Every command takes an explicit `<project_path>` (last path segment is the project name). Deeper paths are fine.

| File | Role in git |
| --- | --- |
| Briefing | Intent — what and why |
| Requirements | Agreed spec. Tasks Breakdown becomes tickets. Not a commit script |
| Ticket | Work item + YAML state (`status`, `depends_on`, `plan_status`) + `## Implementation plan` |
| `Status.md` | Dashboard regenerated by `bora dev status <project_path>` |

Ticket IDs are `YYYYMMDD-NN-slug`, unique **per project**. Don’t rename ticket files.

---

## Dev commands

Every ticket/plan/status command requires `<project_path>` first.

| Command | What it does |
| --- | --- |
| `bora dev init <path> [--tags …] [--force]` | Scaffold briefing, Requirements, `Status.md`, `tickets/`. Writes root `AGENTS.md` only if missing. Don’t use `--force` to upgrade — use `bora dev upgrade`. |
| `bora dev ticket new \| list \| show \| set \| note \| subtask` | Create and update tickets. `set status done` fills `closed`. |
| `bora dev plan show \| set \| task` | Implementation plan **on the ticket**. No `bora dev plan new`, no `bora dev execute` — **go** in chat starts `bora-execute`. |
| `bora dev status <path>` | Regenerate that project’s `Status.md`. |
| `bora dev context <path> [--budget N]` | Print a pasteable briefing for a fresh model. |
| `bora dev lint <path>` | Validate ticket frontmatter and cross-references. |
| `bora dev routing show <path>` | Print model-tier config. Informational; no network. |
| `bora dev upgrade` | Refresh managed `AGENTS.md` + already-installed skills. Does not touch project docs. |
| `bora dev skill install \| uninstall \| list` | Ten-skill pack for `claude`, `cursor`, `opencode`, or `all`. `--project` installs inside the repo. |

Removed since 0.4.5: `bora dev project`, `bora dev decision` (record decisions in Requirements).

---

## AI tool skills

Agentic tools load a `SKILL.md` when its description matches the task. Bora ships ten:

| Skill | When |
| --- | --- |
| `bora` | Session start in a bora project |
| `bora-design` | Architecture before Requirements |
| `bora-plan` | Ticket needs `## Implementation plan` |
| `bora-tdd` | Failing test → code → verify → commit |
| `bora-execute` | You said **go** / resume the board |
| `bora-worktree` | Optional git isolation at execute start |
| `bora-verify` | Before claiming tests/task/ticket/board complete |
| `bora-review` | After a ticket’s last commit, before `done` |
| `bora-debug` | Unexpected verify/build failure (not expected RED) |
| `bora-finish` | Board complete — merge to `origin_branch`, PR, or keep |

```bash
bora dev skill install all              # user-level (~/.cursor/skills, ~/.claude/skills, …)
bora dev skill install cursor --project # committed at .cursor/skills/
bora dev skill list
bora dev skill uninstall cursor --project
```

Uninstall only removes bora-owned skill directories unless you pass `--force`.

| Tool | User-level | Project-level |
| --- | --- | --- |
| `claude` | `~/.claude/skills/` | `.claude/skills/` |
| `cursor` | `~/.cursor/skills/` | `.cursor/skills/` |
| `opencode` | `~/.config/opencode/skills/` | `.opencode/skills/` |

---

## Optional model routing

Advanced. Ignore this unless you want cost-efficiency routing or already use a router. Not part of [Quick start](#quick-start-dev).

Bora does not choose models. Bora identifies the relative reasoning requirements of its workflows and optionally communicates those requirements to compatible routing systems.

On install/upgrade, each skill’s frontmatter includes `model_tier`: `premium`, `standard`, `economy`, or `local`. Hosts that don’t understand the field ignore it. Core skills never embed provider model names.

Three layers:

1. **Repo catalog** — optional `.bora/models.yaml`. Each tier is an **ordered list** of aliases (YAML lists are canonical; comma-separated strings work; a 0.7.0 single string is a one-item list). `init` and `upgrade` never create this file.
2. **Project opt-in** — briefing `routing: true`. `bora dev init` asks (default **no**); `--routing` / `--no-routing` for scripts. Non-TTY init does not prompt.
3. **Session resolve** — every session, fuzzy-match aliases against models **this** Cursor, Claude Code, or OpenCode host can run. Ask if nothing matches or two hits are equally plausible. Optional `routing_cache` on the briefing is a per-tool hint, not the source of truth.

```yaml
routing:
  enabled: true
  tiers:
    premium:
      - grok latest high
      - claude opus
      - gpt-5
    standard:
      - composer
      - sonnet
      - gpt-5-mini
    economy:
      - glm latest
      - haiku
      - gpt-5-nano
    local:
      - ollama
  skills:
    bora-review: economy
```

Cursor and Claude Code are first-class: the **agent** supplies the available-model list; the CLI never queries those products.

```bash
bora dev routing show <project_path>
bora dev routing resolve <project_path> --host cursor --available models.txt
```

`show` prints ordered candidates and whether this project opted in. `resolve` is read-only and takes `--available` (one id or display name per line). Missing yaml → `Status: disabled`, not an error.

OmniRoute remains optional: opaque aliases in the catalog still work when they appear in the host’s available set. Pricing and provider selection stay outside Bora.

---

## For writers

`bora write init` scaffolds a manuscript project. Agents log research; they never write the chapter file.

```text
AGENTS.md
doc/ai/Project.md
Summary.md          ← ephemeral briefing
Chapters/Chapter 001 - The Arrival/
  001 - The Arrival.md              ← author only
  001 - ChapterProject.md           ← beats, notes
  001 - Research.md                 ← AI log
```

```bash
mkdir my-novel && cd my-novel
bora write init
bora write chapter "The Arrival"
bora write status                   # paste into a new chat; save reply as Summary.md
bora write skill install obsidian   # optional vault prompt
```

Chapter IDs increment from the max existing ID (deleting a chapter does not reuse its number). `bora write status` archives `Summary.md` before printing a fresh briefing.

---

## Working across models

Plain Markdown and YAML. Chat-only: paste `bora dev context <path>` or `bora write status`. Agentic tools: read `AGENTS.md` and the skill pack. Local models work the same; run `bora dev lint <path>` after they write tickets.

---

## Upgrading

CLI upgrade does not rewrite a repo. In each project:

```bash
pipx upgrade bora
bora dev upgrade          # AGENTS.md managed region + installed skills
```

**0.6.0 → 0.7.0:** skills gain `model_tier`. No `.bora/models.yaml` is created. Project docs are untouched. 0.6.x projects remain valid.

**0.7.0 → 0.7.5:** catalog tiers may be lists; per-project `routing: true` opt-in; `bora dev routing resolve` matches an injected available-model list. `upgrade` does not create `models.yaml` or add opt-in to existing briefings.

Do not use `bora dev init --force` as an upgrade path. Review `git diff AGENTS.md` and keep local rules under **Project-specific instructions**.

Older jumps (0.5.x skill pack, 0.4.5 hierarchy, 0.3.x `dev`/`write` split): run `bora dev upgrade` the same way. 0.4.5 replaced flat `docs/ai/Project.md` with hierarchical projects; there is no automated migration.

---

## Dev conventions (short)

- **Plans on the ticket**, never Requirements, never `plans/`.
- **`Status.md` is generated.** Update tickets, then `bora dev status <path>`.
- **Commit message:** `{ticket-id} {task-id}: {title}`. One commit per plan task. Bora does not run `git commit`; the agent does, after Commit criteria pass.
- **`AGENTS.md` is root-only.** `upgrade` refreshes the managed region only.
- Decisions go in the Requirements file. There is no `decision` command.

---

## Contributing

```bash
python -m pytest tests/ -v
```

| Module | Role |
| --- | --- |
| `cli.py` | `dev` / `write` commands |
| `routing.py` | Model tiers, catalog lists, session match |
| `ticket.py` / `plan.py` / `status.py` / `lint.py` | Board |
| `skill.py` / `skill_pack.py` | Dev skill pack |
| `templates.py` | Scaffolded files |
| `upgrade.py` | `bora dev upgrade` |
| `writer_*.py` | Write profile |

---

## License

MIT.
