from pathlib import Path

from click.testing import CliRunner

from bora.cli import main

A = "Acme/App"
B = "Other/App"


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
