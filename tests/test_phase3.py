"""Phase 3 integration smoke tests: bora write chapter."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from bora.cli import main


@pytest.fixture
def runner():
    return CliRunner(mix_stderr=False)


@pytest.fixture
def write_project(runner, tmp_path):
    """Return (runner, project_root) for an initialised write project."""
    with runner.isolated_filesystem() as td:
        runner.invoke(main, ["write", "init"])
        yield runner, Path(td)


def _init_and_chapter(runner, name):
    runner.invoke(main, ["write", "init"])
    return runner.invoke(main, ["write", "chapter", name])


def test_chapter_creates_directory(runner):
    with runner.isolated_filesystem() as td:
        runner.invoke(main, ["write", "init"])
        result = runner.invoke(main, ["write", "chapter", "The Beginning"])
        assert result.exit_code == 0, result.output
        assert Path("Chapters/Chapter 001 - The Beginning").is_dir()


def test_chapter_creates_three_files(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["write", "init"])
        runner.invoke(main, ["write", "chapter", "The Beginning"])
        base = Path("Chapters/Chapter 001 - The Beginning")
        assert (base / "001 - The Beginning.md").exists()
        assert (base / "001 - ChapterProject.md").exists()
        assert (base / "001 - Research.md").exists()


def test_manuscript_is_empty(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["write", "init"])
        runner.invoke(main, ["write", "chapter", "The Beginning"])
        manuscript = Path("Chapters/Chapter 001 - The Beginning/001 - The Beginning.md")
        assert manuscript.read_text() == ""


def test_chapter_project_has_correct_frontmatter(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["write", "init"])
        runner.invoke(main, ["write", "chapter", "The Beginning"])
        cp = Path("Chapters/Chapter 001 - The Beginning/001 - ChapterProject.md").read_text()
        assert "chapter: 001" in cp
        assert "status: draft" in cp
        assert "target_words: 0" in cp
        assert "Plot Goals" in cp
        assert "Character Arcs" in cp


def test_research_md_has_header(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["write", "init"])
        runner.invoke(main, ["write", "chapter", "The Beginning"])
        research = Path("Chapters/Chapter 001 - The Beginning/001 - Research.md").read_text()
        assert "# Chapter 001 Research Log" in research
        assert "topic:" in research
        assert "verified: false" in research


def test_sequential_ids_increment(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["write", "init"])
        runner.invoke(main, ["write", "chapter", "First"])
        runner.invoke(main, ["write", "chapter", "Second"])
        assert Path("Chapters/Chapter 001 - First").is_dir()
        assert Path("Chapters/Chapter 002 - Second").is_dir()


def test_id_based_on_max_not_count(runner):
    """Deleting chapter 001 shouldn't cause the next chapter to reuse 001."""
    with runner.isolated_filesystem():
        runner.invoke(main, ["write", "init"])
        runner.invoke(main, ["write", "chapter", "First"])
        runner.invoke(main, ["write", "chapter", "Second"])
        import shutil
        shutil.rmtree("Chapters/Chapter 001 - First")
        runner.invoke(main, ["write", "chapter", "Third"])
        assert Path("Chapters/Chapter 003 - Third").is_dir()


def test_chapters_dir_created_automatically(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["write", "init"])
        assert not Path("Chapters").exists()
        runner.invoke(main, ["write", "chapter", "Intro"])
        assert Path("Chapters").is_dir()
