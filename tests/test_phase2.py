"""Phase 2 integration smoke tests: bora write init scaffolding."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from bora.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_write_init_creates_profile(runner):
    with runner.isolated_filesystem() as td:
        result = runner.invoke(main, ["write", "init"])
        assert result.exit_code == 0, result.output
        prof = json.loads(Path(".bora/profile.json").read_text())
        assert prof["profile"] == "write"
        assert prof["version"] == "0.5.0"


def test_write_init_creates_agents_md(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["write", "init"])
        agents = Path("AGENTS.md").read_text()
        assert "NEVER write manuscript content" in agents
        assert "Research.md" in agents


def test_write_init_creates_project_md(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["write", "init"])
        project = Path("doc/ai/Project.md").read_text()
        assert "profile: write" in project
        assert "status: outline" in project
        assert "Plot Breakdown" in project
        assert "Character Bibles" in project


def test_write_init_creates_summary_md(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["write", "init"])
        summary = Path("Summary.md").read_text()
        assert "profile: write" in summary
        assert "total_words: 0" in summary


def test_write_init_creates_summary_dir(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["write", "init"])
        assert Path("Summary").is_dir()
        assert Path("Summary/.gitkeep").exists()


def test_write_init_refuses_overwrite_without_force(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["write", "init"])
        result = runner.invoke(main, ["write", "init"])
        assert result.exit_code == 1
        assert "Refusing to overwrite" in result.stderr


def test_write_init_force_overwrites(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["write", "init"])
        result = runner.invoke(main, ["write", "init", "--force"])
        assert result.exit_code == 0, result.output


def test_write_init_does_not_create_tickets_dir(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["write", "init"])
        assert not Path("docs/ai/tickets").exists()
