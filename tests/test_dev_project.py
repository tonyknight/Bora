"""Stub tests for removed `bora dev project` and `bora dev decision` commands."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from bora.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_dev_project_removed(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", "Acme/App"])
        result = runner.invoke(main, ["dev", "project", "v1", "nope"])
        assert result.exit_code == 1
        assert "removed in 0.4.5" in result.output.lower() or "removed in 0.4.5" in result.stderr.lower()


def test_dev_decision_removed(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", "Acme/App"])
        result = runner.invoke(main, ["dev", "decision", "new", "Acme/App", "Use SQLite"])
        assert result.exit_code == 1
        assert "removed" in (result.output + result.stderr).lower()


def test_help_hides_removed_commands(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", "Acme/App"])
        result = runner.invoke(main, ["dev", "--help"])
        assert result.exit_code == 0
        assert "project" not in result.output.lower().split() or "bora dev project" not in result.output
        # stronger:
        assert "Archive the current Project.md" not in result.output
        assert "Append a new decision" not in result.output
