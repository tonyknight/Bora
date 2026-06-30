"""Phase 5 integration smoke tests: Obsidian skill, deprecated bora init, end-to-end."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from bora.cli import main


@pytest.fixture
def runner():
    return CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# Obsidian skill install / uninstall
# ---------------------------------------------------------------------------


def test_obsidian_skill_install_creates_files(runner):
    with runner.isolated_filesystem() as td:
        root = Path(td)
        runner.invoke(main, ["write", "init"])
        result = runner.invoke(main, ["write", "skill", "install", "obsidian"])
        assert result.exit_code == 0, result.output
        plugin_dir = root / ".obsidian" / "plugins" / "bora-writer"
        assert plugin_dir.is_dir()
        assert (plugin_dir / "SKILL.md").exists()
        assert (plugin_dir / "manifest.json").exists()
        assert (plugin_dir / "README.md").exists()


def test_obsidian_manifest_is_valid_json(runner):
    with runner.isolated_filesystem() as td:
        root = Path(td)
        runner.invoke(main, ["write", "init"])
        runner.invoke(main, ["write", "skill", "install", "obsidian"])
        manifest = json.loads((root / ".obsidian" / "plugins" / "bora-writer" / "manifest.json").read_text())
        assert manifest["id"] == "bora-writer"
        assert "name" in manifest
        assert "version" in manifest
        assert "minAppVersion" in manifest
        assert "description" in manifest


def test_obsidian_skill_md_has_vault_instructions(runner):
    with runner.isolated_filesystem() as td:
        root = Path(td)
        runner.invoke(main, ["write", "init"])
        runner.invoke(main, ["write", "skill", "install", "obsidian"])
        skill_md = (root / ".obsidian" / "plugins" / "bora-writer" / "SKILL.md").read_text()
        assert "NEVER write manuscript content" in skill_md
        assert "ChapterProject.md" in skill_md


def test_obsidian_skill_install_refuses_overwrite_without_force(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["write", "init"])
        runner.invoke(main, ["write", "skill", "install", "obsidian"])
        result = runner.invoke(main, ["write", "skill", "install", "obsidian"])
        assert result.exit_code == 1
        assert "already exists" in result.stderr


def test_obsidian_skill_install_force_overwrites(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["write", "init"])
        runner.invoke(main, ["write", "skill", "install", "obsidian"])
        result = runner.invoke(main, ["write", "skill", "install", "obsidian", "--force"])
        assert result.exit_code == 0, result.output
        assert "Updated" in result.output


def test_obsidian_skill_uninstall_removes_dir(runner):
    with runner.isolated_filesystem() as td:
        root = Path(td)
        runner.invoke(main, ["write", "init"])
        runner.invoke(main, ["write", "skill", "install", "obsidian"])
        result = runner.invoke(main, ["write", "skill", "uninstall", "obsidian"])
        assert result.exit_code == 0, result.output
        assert not (root / ".obsidian" / "plugins" / "bora-writer").exists()


def test_obsidian_skill_uninstall_when_not_installed(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["write", "init"])
        result = runner.invoke(main, ["write", "skill", "uninstall", "obsidian"])
        assert "not installed" in result.stderr


# ---------------------------------------------------------------------------
# Deprecated bora init stub
# ---------------------------------------------------------------------------


def test_deprecated_init_exits_zero(runner):
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0


def test_deprecated_init_prints_warning(runner):
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init"])
        assert "deprecated" in result.output.lower()
        assert "bora dev init" in result.output
        assert "bora write init" in result.output


# ---------------------------------------------------------------------------
# End-to-end: full dev workflow
# ---------------------------------------------------------------------------


def test_e2e_dev_workflow(runner):
    with runner.isolated_filesystem() as td:
        root = Path(td)

        # Init
        result = runner.invoke(main, ["dev", "init"])
        assert result.exit_code == 0, result.output
        assert (root / ".bora" / "profile.json").exists()

        # Create a ticket
        result = runner.invoke(main, ["dev", "ticket", "new", "My first ticket", "--no-edit"])
        assert result.exit_code == 0, result.output

        # List tickets
        result = runner.invoke(main, ["dev", "ticket", "list"])
        assert result.exit_code == 0, result.output
        assert "My first ticket" in result.output

        # Set status
        ticket_id = next((root / "docs" / "ai" / "tickets").iterdir()).stem
        result = runner.invoke(main, ["dev", "ticket", "set", ticket_id, "status", "in-progress"])
        assert result.exit_code == 0, result.output

        # Lint
        result = runner.invoke(main, ["dev", "lint"])
        assert result.exit_code == 0, result.output
        assert "OK" in result.output

        # Status
        result = runner.invoke(main, ["dev", "status"])
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# End-to-end: full write workflow
# ---------------------------------------------------------------------------


def test_e2e_write_workflow(runner):
    with runner.isolated_filesystem() as td:
        root = Path(td)

        # Init write project
        result = runner.invoke(main, ["write", "init"])
        assert result.exit_code == 0, result.output
        assert json.loads((root / ".bora" / "profile.json").read_text())["profile"] == "write"

        # Create two chapters
        runner.invoke(main, ["write", "chapter", "The Arrival"])
        runner.invoke(main, ["write", "chapter", "The Conflict"])
        assert Path("Chapters/Chapter 001 - The Arrival").is_dir()
        assert Path("Chapters/Chapter 002 - The Conflict").is_dir()

        # Run write status
        result = runner.invoke(main, ["write", "status"])
        assert result.exit_code == 0, result.output
        assert "Chapter 001" in result.output
        assert "Chapter 002" in result.output

        # Save output as Summary.md and run status again (archive test)
        (root / "Summary.md").write_text("# Summary content\n", encoding="utf-8")
        result = runner.invoke(main, ["write", "status"])
        assert result.exit_code == 0, result.output
        archives = list((root / "Summary").glob("*.md"))
        assert any("Summary.md" in f.name for f in archives)

        # Install Obsidian skill
        result = runner.invoke(main, ["write", "skill", "install", "obsidian"])
        assert result.exit_code == 0, result.output
        assert (root / ".obsidian" / "plugins" / "bora-writer").is_dir()

        # Uninstall Obsidian skill
        result = runner.invoke(main, ["write", "skill", "uninstall", "obsidian"])
        assert result.exit_code == 0, result.output
        assert not (root / ".obsidian" / "plugins" / "bora-writer").exists()
