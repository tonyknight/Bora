from pathlib import Path

import pytest
from click.testing import CliRunner

from bora.cli import main

A = "Acme/App"
B = "Other/App"
NEVER = "Acme/Never"

NEVER_INITED_COMMANDS = [
    ["dev", "ticket", "new", NEVER, "A ticket", "--no-edit"],
    ["dev", "status", NEVER],
    ["dev", "lint", NEVER],
    ["dev", "context", NEVER],
]


def test_tickets_are_isolated_per_project():
    runner = CliRunner()
    with runner.isolated_filesystem():
        assert runner.invoke(main, ["dev", "init", A]).exit_code == 0
        assert runner.invoke(main, ["dev", "init", B]).exit_code == 0
        r = runner.invoke(main, ["dev", "ticket", "new", A, "Alpha ticket", "--no-edit"])
        assert r.exit_code == 0, r.output
        listed_b = runner.invoke(main, ["dev", "ticket", "list", B])
        assert "Alpha ticket" not in listed_b.output
        listed_a = runner.invoke(main, ["dev", "ticket", "list", A])
        assert "Alpha ticket" in listed_a.output
        assert (Path("docs/ai/Acme/App/tickets")).exists()
        assert not (Path("docs/ai/tickets")).exists()


def test_context_includes_requirements_and_status():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", A])
        runner.invoke(main, ["dev", "ticket", "new", A, "Work item", "--no-edit"])
        result = runner.invoke(main, ["dev", "context", A])
        assert result.exit_code == 0, result.output
        assert "AGENTS.md" in result.output
        assert "Requirements.md" in result.output
        assert "Status.md" in result.output
        assert "===== docs/ai/Architecture.md =====" not in result.output


def test_lint_rejects_cross_project_depends_on():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", A])
        runner.invoke(main, ["dev", "init", B])
        runner.invoke(main, ["dev", "ticket", "new", B, "Other work", "--no-edit"])
        other_id = next(Path("docs/ai/Other/App/tickets").glob("*.md")).stem
        runner.invoke(main, ["dev", "ticket", "new", A, "Needs other", "--no-edit"])
        a_path = next(Path("docs/ai/Acme/App/tickets").glob("*.md"))
        text = a_path.read_text()
        text = text.replace("depends_on: []", f"depends_on: [{other_id}]")
        a_path.write_text(text)
        result = runner.invoke(main, ["dev", "lint", A])
        assert result.exit_code == 1
        assert "unknown ticket" in result.stderr.lower() or "unknown" in result.stderr


def _err(result) -> str:
    return (result.stderr or "") + (result.output or "")


@pytest.mark.parametrize("args", NEVER_INITED_COMMANDS)
def test_never_inited_project_is_rejected(args):
    runner = CliRunner()
    with runner.isolated_filesystem():
        assert runner.invoke(main, ["dev", "init", B]).exit_code == 0
        result = runner.invoke(main, args)
        assert result.exit_code == 1, result.output
        err = _err(result).lower()
        assert "briefing" in err
        assert "(yyyy-mm-dd)" in err
        assert "never.md" in err or "{projectname}.md" in err
        assert not Path("docs/ai/Acme/Never").exists()


def test_commands_work_after_real_init():
    runner = CliRunner()
    with runner.isolated_filesystem():
        assert runner.invoke(main, ["dev", "init", NEVER]).exit_code == 0
        new = runner.invoke(main, ["dev", "ticket", "new", NEVER, "Hello", "--no-edit"])
        assert new.exit_code == 0, new.output
        status = runner.invoke(main, ["dev", "status", NEVER])
        assert status.exit_code == 0, status.output
        lint = runner.invoke(main, ["dev", "lint", NEVER])
        assert lint.exit_code == 0, lint.output
        ctx = runner.invoke(main, ["dev", "context", NEVER])
        assert ctx.exit_code == 0, ctx.output
        assert Path("docs/ai/Acme/Never").is_dir()
