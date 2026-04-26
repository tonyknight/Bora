# bora

> Brazilian Portuguese for *let's go*.

A structured collaboration framework for human–AI coding projects.

`bora` is a small CLI that scaffolds and maintains a documentation
convention designed for working with AI coding agents across multiple
sessions and multiple models. The files it generates live alongside your
code in version control, so any model — Claude, GPT, Gemini, a local
Llama — can read them and get oriented before writing a line.

## Why

When you collaborate with AI on a project that takes more than one
session, two problems compound:

1. **Context decay.** Every new chat starts from zero. You re-explain the
   project from memory, often inconsistently.
2. **Model switching cost.** Different models see different versions of
   your project. Switching means re-briefing.

`bora` addresses both by keeping a small, structured set of Markdown
files in your repo:

- `AGENTS.md` — operating instructions for AI agents.
- `docs/ai/Project.md` — what we're building and why.
- `docs/ai/Architecture.md` — how we've decided to build it, plus a
  decision log.
- `docs/ai/Tasks.md` — auto-generated dashboard of current work.
- `docs/ai/tickets/*.md` — the tickets themselves, with YAML frontmatter
  and Markdown body.

The CLI handles the mechanics: ticket creation with chronological IDs,
status updates, frontmatter validation, dashboard regeneration, and
briefing assembly with an optional token budget.

## Installation

`bora` is a Python CLI. The recommended way to install Python CLIs
globally is **pipx**, which puts the `bora` command on your `PATH`
without polluting your system Python.

### Option 1: pipx (recommended)

If you don't already have pipx:

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

After `pipx ensurepath` you may need to open a new terminal so the
updated `PATH` takes effect.

Then install `bora`:

```bash
# Once published to PyPI:
pipx install bora

# Until then, install directly from GitHub:
pipx install git+https://github.com/yourname/bora.git
```

Verify:

```bash
bora --version
```

To upgrade later:

```bash
pipx upgrade bora
```

To uninstall:

```bash
pipx uninstall bora
```

### Option 2: pip --user

If you don't want to install pipx, you can use `pip --user`:

```bash
pip install --user bora
# or, from GitHub:
pip install --user git+https://github.com/yourname/bora.git
```

This installs into your user site-packages and puts the `bora` script
in your user binary directory (typically `~/.local/bin` on Linux/macOS,
`%APPDATA%\Python\Scripts` on Windows). If `bora` isn't found after
install, see *Troubleshooting PATH* below.

### Option 3: Development install

If you've cloned the repository and want to hack on `bora`:

```bash
git clone https://github.com/yourname/bora.git
cd bora
pip install -e .
```

The `-e` flag installs in editable mode, so changes to the source take
effect without reinstalling.

### Troubleshooting PATH

If you installed with `pip --user` and get `bora: command not found`,
your user binary directory probably isn't on `PATH`.

Find where pip installed the script:

```bash
python3 -m site --user-base
```

The script lives in `<user-base>/bin` on Linux/macOS or
`<user-base>\Scripts` on Windows. Add that directory to your shell's
`PATH` — for bash/zsh, append to `~/.bashrc` or `~/.zshrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then `source` the file or open a new terminal.

This is the main reason pipx is recommended: it handles `PATH` for you.

## Quick start

```bash
cd /path/to/your/repo
bora init                              # scaffold AGENTS.md and docs/ai/
$EDITOR docs/ai/Project.md             # describe what you're building
bora ticket new "Set up database" --priority high
bora ticket set 01 status in-progress  # fuzzy id match works
bora status                            # regenerate Tasks.md
bora context --budget 8000             # print briefing for a fresh model session
```

To brief a new chat session with a model, `bora context` prints all the
files an AI agent should read, in order. Pipe it to your clipboard:

```bash
bora context | pbcopy            # macOS
bora context | xclip -selection clipboard  # Linux with xclip
bora context | clip              # Windows
```

Paste it as the first message of your conversation.

## Commands

| Command                                  | What it does                                            |
| ---------------------------------------- | ------------------------------------------------------- |
| `bora init`                              | Scaffold `AGENTS.md` and `docs/ai/` in the current dir. |
| `bora ticket new "<title>"`              | Create a new ticket. Options: `--type`, `--priority`, `--parent`. |
| `bora ticket list`                       | List tickets. Filters: `--status`, `--type`, `--priority`, `--blocked`. |
| `bora ticket show <id>`                  | Print a ticket's contents. Fuzzy ID match supported.    |
| `bora ticket set <id> <field> <value>`   | Update a frontmatter field.                             |
| `bora ticket subtask <id> <sub-id> <status>` | Update a frontmatter subtask's status.              |
| `bora ticket note <id> "<text>"`         | Append a dated entry to the body Notes section.         |
| `bora status`                            | Regenerate `Tasks.md`.                                  |
| `bora context [--budget N]`              | Print briefing content, optionally token-bounded.       |
| `bora lint`                              | Validate frontmatter and cross-references.              |
| `bora decision new "<title>"`            | Append a templated decision entry to `Architecture.md`. |

Run `bora <command> --help` for full options on any command.

## Conventions

- **Ticket IDs** are `YYYYMMDD-NN-slug`. The CLI generates them; don't
  pick your own.
- **`Tasks.md` is auto-generated.** Never hand-edit it. Update tickets
  and run `bora status`.
- **Subtasks live in two places by design.** Major subtasks go in
  frontmatter (queryable, appear in `Tasks.md` aggregation). Small
  subtasks are body checkboxes (counted but not aggregated by id).
- **Decisions append to `Architecture.md`.** Don't rewrite history; add
  new entries when the design evolves.
- **AGENTS.md is the entry point for any AI tool.** Tools like Claude
  Code, Cursor, and others increasingly look for this file at repo root.

## Working with multiple models

`bora` is model-agnostic by design. It produces plain Markdown and YAML
that any LLM can read. Patterns that work well:

- **For chat-only models** (web Claude, ChatGPT, etc.), run
  `bora context --budget <N>` and paste the output as your first
  message. The model now has the same briefing every other model gets.
- **For agentic tools with file access** (Claude Code, Cursor, Aider),
  the model reads `AGENTS.md` and follows its instructions to discover
  the rest. The CLI is callable from the agent's shell, so the model
  can run `bora ticket set ...` directly as work progresses.
- **For local models**, the same flow works. Smaller models (under ~14B)
  may struggle with structured frontmatter — run `bora lint` after any
  model writes to a ticket file to catch errors.

## Contributing

Contributions welcome. The code is in `bora/`:

- `paths.py` — repo-root detection and shared constants.
- `ticket.py` — frontmatter parsing, fuzzy ID matching, body progress.
- `templates.py` — scaffolded files (AGENTS.md, Project.md, etc.).
- `lint.py` — validation rules.
- `status.py` — `Tasks.md` generation.
- `create.py` — chronological ID generation.
- `context.py` — briefing assembly.
- `cli.py` — Click-based command surface.

Before opening a PR, run through the smoke test in a scratch directory:

```bash
mkdir /tmp/test-bora && cd /tmp/test-bora && git init
bora init
bora ticket new "Test ticket" --priority high
bora ticket set 01 status in-progress
bora status
bora lint
```

## Publishing to PyPI (maintainer notes)

When you're ready to publish:

1. Confirm the package name `bora` is available at
   https://pypi.org/project/bora/. If taken, change `name` in
   `pyproject.toml` (consider `bora-cli` while keeping the command
   itself as `bora`).
2. Update `authors` and the `[project.urls]` block in `pyproject.toml`
   to point at your GitHub.
3. Bump `version` in both `pyproject.toml` and `bora/__init__.py`.
4. Build and upload:

   ```bash
   pip install --upgrade build twine
   python -m build
   twine upload dist/*
   ```

5. Tag the release in git:

   ```bash
   git tag v0.1.0
   git push --tags
   ```

## License

MIT. See `LICENSE` if added, or change in `pyproject.toml` to taste.
