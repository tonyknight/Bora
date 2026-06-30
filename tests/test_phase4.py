"""Phase 4 integration smoke tests: bora write status and summary archival."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from bora.cli import main


@pytest.fixture
def runner():
    return CliRunner(mix_stderr=False)


def _setup_write_project(runner):
    runner.invoke(main, ["write", "init"])


def test_write_status_exits_ok(runner):
    with runner.isolated_filesystem():
        _setup_write_project(runner)
        result = runner.invoke(main, ["write", "status"])
        assert result.exit_code == 0, result.output


def test_write_status_output_has_frontmatter(runner):
    with runner.isolated_filesystem():
        _setup_write_project(runner)
        result = runner.invoke(main, ["write", "status"])
        output = result.output
        assert "profile: write" in output
        assert "total_words:" in output
        assert "word_count_approximate: true" in output
        assert "chapters_completed:" in output


def test_write_status_output_has_sections(runner):
    with runner.isolated_filesystem():
        _setup_write_project(runner)
        result = runner.invoke(main, ["write", "status"])
        output = result.output
        assert "# Story Synopsis" in output
        assert "## Chapter Status" in output
        assert "## Aggregate Stats" in output
        assert "## Context State" in output
        assert "Run your AI model with this output" in output


def test_write_status_includes_chapter_info(runner):
    with runner.isolated_filesystem():
        _setup_write_project(runner)
        runner.invoke(main, ["write", "chapter", "The Beginning"])
        runner.invoke(main, ["write", "chapter", "Rising Action"])
        result = runner.invoke(main, ["write", "status"])
        output = result.output
        assert "Chapter 001" in output
        assert "The Beginning" in output
        assert "Chapter 002" in output
        assert "Rising Action" in output


def test_write_status_archives_existing_summary(runner):
    with runner.isolated_filesystem() as td:
        root = Path(td)
        _setup_write_project(runner)

        # Write an existing Summary.md
        (root / "Summary.md").write_text("# Old Summary\n", encoding="utf-8")

        runner.invoke(main, ["write", "status"])

        # Original should be gone, archived copy should exist
        assert not (root / "Summary.md").exists()
        archives = list((root / "Summary").glob("*.md"))
        # Filter out .gitkeep
        md_files = [f for f in archives if not f.name.startswith(".")]
        assert len(md_files) == 1
        assert "Summary.md" in md_files[0].name


def test_write_status_safe_to_rerun(runner):
    """Running status twice should archive once and produce clean output both times."""
    with runner.isolated_filesystem() as td:
        root = Path(td)
        _setup_write_project(runner)

        result1 = runner.invoke(main, ["write", "status"])
        assert result1.exit_code == 0

        # Write a Summary.md to simulate the user saving the output
        (root / "Summary.md").write_text("# Summary\n", encoding="utf-8")

        result2 = runner.invoke(main, ["write", "status"])
        assert result2.exit_code == 0

        # Two archives: one from the init-created Summary.md, one from the user-written one
        archives = [f for f in (root / "Summary").iterdir() if f.suffix == ".md"]
        assert len(archives) == 2


def test_write_status_archive_collision_suffix(runner):
    """Two archives on the same day get (1), (2) suffixes."""
    with runner.isolated_filesystem() as td:
        root = Path(td)
        _setup_write_project(runner)
        from datetime import date

        today = date.today().isoformat()
        summary_dir = root / "Summary"
        summary_dir.mkdir(exist_ok=True)

        # Pre-seed an archive with today's date
        (summary_dir / f"{today} - Summary.md").write_text("old", encoding="utf-8")

        # Now write a Summary.md and run status
        (root / "Summary.md").write_text("newer", encoding="utf-8")
        runner.invoke(main, ["write", "status"])

        assert (summary_dir / f"{today} - Summary (1).md").exists()
