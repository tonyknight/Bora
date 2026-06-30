"""Chapter scaffolding: bora write chapter."""

from __future__ import annotations

import re
from pathlib import Path

import click

from .templates import WRITER_CHAPTER_PROJECT_MD, WRITER_RESEARCH_MD


def _next_chapter_id(chapters_root: Path) -> int:
    """Scan existing Chapter NNN - * directories and return the next ID."""
    max_id = 0
    if chapters_root.exists():
        pattern = re.compile(r"^Chapter (\d{3}) - .+$")
        for entry in chapters_root.iterdir():
            if entry.is_dir():
                m = pattern.match(entry.name)
                if m:
                    max_id = max(max_id, int(m.group(1)))
    return max_id + 1


def create_chapter(project_root: Path, name: str) -> Path:
    """Scaffold a new chapter directory with its three files.

    Returns the path to the created chapter directory.
    """
    chapters_root = project_root / "Chapters"
    chapter_id = _next_chapter_id(chapters_root)
    padded = f"{chapter_id:03d}"

    chapter_dir = chapters_root / f"Chapter {padded} - {name}"
    chapter_dir.mkdir(parents=True, exist_ok=True)

    # Empty manuscript — agents must never write to this file
    manuscript = chapter_dir / f"{padded} - {name}.md"
    manuscript.write_text("", encoding="utf-8")

    chapter_project = chapter_dir / f"{padded} - ChapterProject.md"
    chapter_project.write_text(
        WRITER_CHAPTER_PROJECT_MD.format(padded=padded, name=name),
        encoding="utf-8",
    )

    research = chapter_dir / f"{padded} - Research.md"
    research.write_text(
        WRITER_RESEARCH_MD.format(padded=padded),
        encoding="utf-8",
    )

    click.echo(f"Created {chapter_dir.relative_to(project_root)}/")
    click.echo(f"  {manuscript.name}")
    click.echo(f"  {chapter_project.name}")
    click.echo(f"  {research.name}")

    return chapter_dir
