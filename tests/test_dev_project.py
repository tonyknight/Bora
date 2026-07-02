"""Integration tests for bora dev project (v0.3.5)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from bora.cli import main
from bora.dev_project import write_project_json
from bora.paths import find_project_file


TODAY = date.today().isoformat()


@pytest.fixture
def runner():
    return CliRunner(mix_stderr=False)


@pytest.fixture
def dev_project(runner):
    """Yield (runner, root) for an initialised dev project with one done ticket."""
    with runner.isolated_filesystem() as td:
        root = Path(td)
        runner.invoke(main, ["dev", "init"])
        # Create and close a ticket so archive captures it
        runner.invoke(main, ["dev", "ticket", "new", "Scaffold the thing", "--no-edit"])
        ticket_id = next((root / "docs" / "ai" / "tickets").iterdir()).stem
        runner.invoke(main, ["dev", "ticket", "set", ticket_id, "status", "done"])
        yield runner, root


# ---------------------------------------------------------------------------
# find_project_file
# ---------------------------------------------------------------------------

def test_find_project_file_uses_project_json(runner):
    with runner.isolated_filesystem() as td:
        root = Path(td)
        runner.invoke(main, ["dev", "init"])
        # project.json points to Project.md
        assert find_project_file(root) == root / "docs" / "ai" / "Project.md"


def test_find_project_file_follows_active_after_project_command(dev_project):
    runner, root = dev_project
    runner.invoke(main, ["dev", "project", "v0.3.5", "New description"])
    found = find_project_file(root)
    assert found is not None
    assert found.name == f"({TODAY}) Project.md"


def test_find_project_file_falls_back_to_plain(runner):
    with runner.isolated_filesystem() as td:
        root = Path(td)
        # No project.json, just a plain Project.md
        (root / "docs" / "ai").mkdir(parents=True)
        (root / "docs" / "ai" / "Project.md").write_text("# Project\n")
        assert find_project_file(root) == root / "docs" / "ai" / "Project.md"


def test_find_project_file_returns_none_when_missing(runner):
    with runner.isolated_filesystem() as td:
        root = Path(td)
        assert find_project_file(root) is None


# ---------------------------------------------------------------------------
# bora dev project — basic output
# ---------------------------------------------------------------------------

def test_dev_project_exits_ok(dev_project):
    runner, root = dev_project
    result = runner.invoke(main, ["dev", "project", "v0.3.5", "A fresh start"])
    assert result.exit_code == 0, result.output


def test_dev_project_creates_new_project_file(dev_project):
    runner, root = dev_project
    runner.invoke(main, ["dev", "project", "v0.3.5", "A fresh start"])
    new_file = root / "docs" / "ai" / f"({TODAY}) Project.md"
    assert new_file.exists()


def test_dev_project_new_file_has_correct_frontmatter(dev_project):
    runner, root = dev_project
    runner.invoke(main, ["dev", "project", "v0.3.5", "A fresh start"])
    new_file = root / "docs" / "ai" / f"({TODAY}) Project.md"
    fm_text = new_file.read_text()
    assert fm_text.startswith("---")
    end = fm_text.find("\n---", 3)
    fm = yaml.safe_load(fm_text[3:end])
    assert fm["version"] == "v0.3.5"
    assert fm["description"] == "A fresh start"
    assert fm["status"] == "open"
    assert fm["start_date"] == TODAY


def test_dev_project_updates_project_json(dev_project):
    runner, root = dev_project
    runner.invoke(main, ["dev", "project", "v0.3.5", "A fresh start"])
    data = json.loads((root / ".bora" / "project.json").read_text())
    assert data["active"] == f"({TODAY}) Project.md"
    assert data["version"] == "v0.3.5"


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------

def test_dev_project_archives_old_project(dev_project):
    runner, root = dev_project
    runner.invoke(main, ["dev", "project", "v0.3.5", "A fresh start"])
    archive_dir = root / "docs" / "ai" / "Projects"
    assert archive_dir.is_dir()
    archived_files = list(archive_dir.glob("*.md"))
    assert len(archived_files) == 1


def test_dev_project_archive_has_date_prefix_when_plain(dev_project):
    runner, root = dev_project
    runner.invoke(main, ["dev", "project", "v0.3.5", "A fresh start"])
    archive_dir = root / "docs" / "ai" / "Projects"
    archived = list(archive_dir.glob("*.md"))[0]
    assert archived.name == f"({TODAY}) Project.md"


def test_dev_project_archive_keeps_existing_date_prefix(runner):
    with runner.isolated_filesystem() as td:
        root = Path(td)
        runner.invoke(main, ["dev", "init"])
        # Manually rename to simulate a previously dated project file
        old = root / "docs" / "ai" / "Project.md"
        dated = root / "docs" / "ai" / "(2026-06-01) Project.md"
        old.rename(dated)
        write_project_json(root, {"active": "(2026-06-01) Project.md", "version": "v0.3.0"})

        runner.invoke(main, ["dev", "project", "v0.3.5", "Next version"])
        archive_dir = root / "docs" / "ai" / "Projects"
        archived = list(archive_dir.glob("*.md"))[0]
        # Should NOT re-prefix with today's date — keep original date prefix
        assert archived.name == "(2026-06-01) Project.md"


def test_dev_project_archive_frontmatter_has_archival_fields(dev_project):
    runner, root = dev_project
    runner.invoke(main, ["dev", "project", "v0.3.5", "A fresh start"])
    archive_dir = root / "docs" / "ai" / "Projects"
    archived = list(archive_dir.glob("*.md"))[0]
    fm_text = archived.read_text()
    end = fm_text.find("\n---", 3)
    fm = yaml.safe_load(fm_text[3:end])
    assert fm["status"] == "archived"
    assert fm["archived_date"] == TODAY
    assert fm["archived_at_version"] == "v0.3.5"


def test_dev_project_archive_includes_completed_tickets(dev_project):
    runner, root = dev_project
    runner.invoke(main, ["dev", "project", "v0.3.5", "A fresh start"])
    archive_dir = root / "docs" / "ai" / "Projects"
    archived = list(archive_dir.glob("*.md"))[0]
    fm_text = archived.read_text()
    end = fm_text.find("\n---", 3)
    fm = yaml.safe_load(fm_text[3:end])
    assert "completed_tickets" in fm
    assert len(fm["completed_tickets"]) == 1
    assert fm["completed_tickets"][0]["title"] == "Scaffold the thing"


def test_dev_project_archive_collision_suffix(dev_project):
    runner, root = dev_project
    # Pre-seed an archive file with today's date to force a collision
    projects_dir = root / "docs" / "ai" / "Projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    (projects_dir / f"({TODAY}) Project.md").write_text("existing archive")

    runner.invoke(main, ["dev", "project", "v0.3.5", "A fresh start"])
    assert (projects_dir / f"({TODAY}) Project (1).md").exists()


# ---------------------------------------------------------------------------
# No existing project file (edge case — skip archive)
# ---------------------------------------------------------------------------

def test_dev_project_no_existing_file_creates_new(runner):
    with runner.isolated_filesystem() as td:
        root = Path(td)
        runner.invoke(main, ["dev", "init"])
        # Remove the project file to simulate the edge case
        (root / "docs" / "ai" / "Project.md").unlink()
        write_project_json(root, {"active": "Project.md", "version": ""})

        result = runner.invoke(main, ["dev", "project", "v0.3.5", "Starting fresh"])
        assert result.exit_code == 0, result.output
        assert (root / "docs" / "ai" / f"({TODAY}) Project.md").exists()
        # No archive dir created since there was nothing to archive
        assert not (root / "docs" / "ai" / "Projects").exists()


# ---------------------------------------------------------------------------
# Description truncation
# ---------------------------------------------------------------------------

def test_description_truncated_to_280_chars(dev_project):
    runner, root = dev_project
    long_desc = "x" * 400
    runner.invoke(main, ["dev", "project", "v0.3.5", long_desc])
    new_file = root / "docs" / "ai" / f"({TODAY}) Project.md"
    fm_text = new_file.read_text()
    end = fm_text.find("\n---", 3)
    fm = yaml.safe_load(fm_text[3:end])
    assert len(fm["description"]) == 280


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------

def test_dev_project_prompts_for_missing_version(dev_project):
    runner, root = dev_project
    result = runner.invoke(main, ["dev", "project"], input="v0.3.5\nA description\n")
    assert result.exit_code == 0, result.output
    assert (root / "docs" / "ai" / f"({TODAY}) Project.md").exists()


def test_dev_project_prompts_for_missing_description(dev_project):
    runner, root = dev_project
    result = runner.invoke(main, ["dev", "project", "v0.3.5"], input="A description\n")
    assert result.exit_code == 0, result.output
    new_file = root / "docs" / "ai" / f"({TODAY}) Project.md"
    fm_text = new_file.read_text()
    end = fm_text.find("\n---", 3)
    fm = yaml.safe_load(fm_text[3:end])
    assert fm["description"] == "A description"
