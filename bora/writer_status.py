"""Status and summary pipeline: bora write status."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Optional

import yaml


def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter block from a markdown string."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:]
    return text


def _count_words(text: str) -> int:
    """Approximate word count: strip frontmatter, split on whitespace."""
    body = _strip_frontmatter(text)
    return len(body.split())


def _load_frontmatter(text: str) -> dict:
    """Parse only the YAML frontmatter block from a markdown string."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        return {}


def _count_research_topics(text: str) -> int:
    """Count ## Topic: headings in a Research.md file."""
    return len(re.findall(r"^## Topic:", text, re.MULTILINE))


def _archive_summary(project_root: Path) -> Optional[Path]:
    """Move Summary.md → Summary/(YYYY-MM-DD) - Summary.md if it exists.

    Returns the archive path, or None if there was nothing to archive.
    """
    summary = project_root / "Summary.md"
    if not summary.exists():
        return None

    archive_dir = project_root / "Summary"
    archive_dir.mkdir(exist_ok=True)

    today = date.today().isoformat()
    base_name = f"({today}) Summary.md"
    dest = archive_dir / base_name

    # Avoid collision by appending (N)
    n = 1
    while dest.exists():
        dest = archive_dir / f"({today}) Summary ({n}).md"
        n += 1

    summary.rename(dest)
    return dest


def compile_status(project_root: Path) -> str:
    """Read the write project and return a structured briefing string for stdout."""
    project_md_path = project_root / "doc" / "ai" / "Project.md"
    chapters_root = project_root / "Chapters"

    # Archive existing Summary.md first
    archived = _archive_summary(project_root)

    # --- Project overview ---
    project_text = project_md_path.read_text(encoding="utf-8") if project_md_path.exists() else ""
    project_fm = _load_frontmatter(project_text)
    project_body = _strip_frontmatter(project_text).strip()

    # --- Chapter data ---
    chapters = []
    if chapters_root.exists():
        chapter_dir_pattern = re.compile(r"^Chapter (\d{3}) - (.+)$")
        for entry in sorted(chapters_root.iterdir()):
            if not entry.is_dir():
                continue
            m = chapter_dir_pattern.match(entry.name)
            if not m:
                continue
            chapter_id, chapter_name = m.group(1), m.group(2)

            # Manuscript word count
            manuscript = entry / f"{chapter_id} - {chapter_name}.md"
            word_count = _count_words(manuscript.read_text(encoding="utf-8")) if manuscript.exists() else 0

            # ChapterProject.md status + metadata
            cp_path = entry / f"{chapter_id} - ChapterProject.md"
            cp_text = cp_path.read_text(encoding="utf-8") if cp_path.exists() else ""
            cp_fm = _load_frontmatter(cp_text)
            status = cp_fm.get("status", "draft")
            target_words = cp_fm.get("target_words", 0)

            # Research topic count
            research_path = entry / f"{chapter_id} - Research.md"
            research_text = research_path.read_text(encoding="utf-8") if research_path.exists() else ""
            topic_count = _count_research_topics(research_text)

            chapters.append({
                "id": chapter_id,
                "name": chapter_name,
                "status": status,
                "word_count": word_count,
                "target_words": target_words,
                "research_topics": topic_count,
            })

    total_words = sum(c["word_count"] for c in chapters)
    completed = sum(1 for c in chapters if c["status"] == "completed")
    in_progress = sum(1 for c in chapters if c["status"] == "in-progress")
    draft = sum(1 for c in chapters if c["status"] == "draft")

    today = date.today().isoformat()

    # --- Build output ---
    lines = []

    # YAML frontmatter template (pre-filled)
    lines.append("---")
    lines.append(f"profile: write")
    lines.append(f"last_generated: \"{today}\"")
    lines.append(f"total_words: {total_words}")
    lines.append(f"word_count_approximate: true")
    lines.append(f"chapters_completed: {completed}")
    lines.append(f"chapters_in_progress: {in_progress}")
    lines.append(f"chapters_draft: {draft}")
    lines.append(f"status: active")
    lines.append("---")
    lines.append("")

    # Story synopsis from Project.md
    lines.append("# Story Synopsis")
    lines.append("")
    if project_body:
        lines.append(project_body)
    else:
        lines.append("_(Project.md not found or empty.)_")
    lines.append("")

    # Chapter-by-chapter status
    lines.append("## Chapter Status")
    lines.append("")
    if chapters:
        for c in chapters:
            lines.append(
                f"- **Chapter {c['id']} — {c['name']}**: {c['status']}"
                f" | ~{c['word_count']} words"
                f" | {c['research_topics']} research topic(s)"
            )
    else:
        lines.append("_(No chapters yet.)_")
    lines.append("")

    # Aggregate stats
    lines.append("## Aggregate Stats")
    lines.append("")
    lines.append(f"- Total chapters: {len(chapters)}")
    lines.append(f"- Completed: {completed}  |  In progress: {in_progress}  |  Draft: {draft}")
    lines.append(f"- Total words (approximate): {total_words}")
    lines.append("")

    # Context state
    lines.append("## Context State")
    lines.append("")
    in_progress_chapters = [c for c in chapters if c["status"] == "in-progress"]
    if in_progress_chapters:
        next_focus = in_progress_chapters[-1]
        lines.append(f"- Next chapter focus: **Chapter {next_focus['id']} — {next_focus['name']}**")
    else:
        lines.append("- No chapters currently in progress.")
    lines.append("")

    if archived:
        lines.append(f"_(Previous Summary.md archived to Summary/{archived.name})_")
        lines.append("")

    lines.append("> Run your AI model with this output, then save as Summary.md")
    lines.append("")

    return "\n".join(lines)
