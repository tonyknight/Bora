from pathlib import Path

import pytest
from click.testing import CliRunner

from bora.cli import main

SAMPLE = "Acme/Auth"


def test_status_writes_status_md_not_tasks_md():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        result = runner.invoke(main, ["dev", "status", SAMPLE])
        assert result.exit_code == 0, result.output
        status = Path("docs/ai/Acme/Auth/Status.md")
        assert status.exists()
        text = status.read_text()
        assert text.startswith("# Status")
        assert "Do not hand-edit" in text
        assert not Path("docs/ai/Tasks.md").exists()


def test_status_without_path_errors():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        result = runner.invoke(main, ["dev", "status"])
        assert result.exit_code != 0


def test_status_md_has_dashboard_sections():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        result = runner.invoke(main, ["dev", "status", SAMPLE])
        assert result.exit_code == 0, result.output
        text = Path("docs/ai/Acme/Auth/Status.md").read_text()
        assert "bora dev status" in text
        assert "## In progress" in text
        assert "## Blocked" in text
        assert "## Up next" in text
        assert "## Recently completed" in text
        assert "## Stats" in text


def test_status_focus_comes_from_dated_briefing():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        briefing = next(
            p for p in Path("docs/ai/Acme/Auth").iterdir()
            if p.suffix == ".md" and "Requirements" not in p.name and p.name != "Status.md"
        )
        text = briefing.read_text()
        briefing.write_text(text.replace('focus: ""', 'focus: "Ship the login flow"'), encoding="utf-8")
        result = runner.invoke(main, ["dev", "status", SAMPLE])
        assert result.exit_code == 0, result.output
        status = Path("docs/ai/Acme/Auth/Status.md").read_text()
        assert "## Current focus" in status
        assert "Ship the login flow" in status


def test_write_tasks_md_raises():
    from bora.status import write_tasks_md

    with pytest.raises(RuntimeError, match="use write_status_md"):
        write_tasks_md(Path("."))


def test_ticket_new_regenerates_status_md():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        result = runner.invoke(main, ["dev", "ticket", "new", SAMPLE, "A ticket", "--no-edit"])
        assert result.exit_code == 0, result.output
        assert not Path("docs/ai/Tasks.md").exists()
        status = Path("docs/ai/Acme/Auth/Status.md").read_text()
        assert "A ticket" in status
        assert "Status.md updated" in result.stderr
