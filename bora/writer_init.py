"""Writer profile initialisation: bora write init."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from .profile import write_profile
from .templates import (
    WRITER_AGENTS_MD,
    WRITER_PROJECT_MD,
    WRITER_SUMMARY_MD,
)


def init_writer_project(root: Path, force: bool = False) -> None:
    """Scaffold a write-profile project in `root`."""
    profile_json = root / ".bora" / "profile.json"
    agents_md = root / "AGENTS.md"
    project_md = root / "doc" / "ai" / "Project.md"
    summary_md = root / "Summary.md"
    summary_dir = root / "Summary"

    if not force:
        existing = [p for p in [profile_json, agents_md, project_md, summary_md] if p.exists()]
        if existing:
            click.echo("Refusing to overwrite existing files:", err=True)
            for p in existing:
                try:
                    click.echo(f"  {p.relative_to(root)}", err=True)
                except ValueError:
                    click.echo(f"  {p}", err=True)
            click.echo("Use --force to overwrite.", err=True)
            sys.exit(1)

    write_profile(root, "write")
    click.echo("Created .bora/profile.json")

    agents_md.write_text(WRITER_AGENTS_MD, encoding="utf-8")
    click.echo("Created AGENTS.md")

    project_md.parent.mkdir(parents=True, exist_ok=True)
    project_md.write_text(WRITER_PROJECT_MD, encoding="utf-8")
    click.echo("Created doc/ai/Project.md")

    summary_md.write_text(WRITER_SUMMARY_MD, encoding="utf-8")
    click.echo("Created Summary.md")

    summary_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = summary_dir / ".gitkeep"
    gitkeep.write_text("", encoding="utf-8")
    click.echo("Created Summary/")

    click.echo("\nWrite project scaffolded. Next steps:")
    click.echo("  1. Edit AGENTS.md to orient your AI model to this project.")
    click.echo("  2. Edit doc/ai/Project.md with your story's premise and structure.")
    click.echo("  3. Create your first chapter: bora write chapter \"<chapter title>\"")
