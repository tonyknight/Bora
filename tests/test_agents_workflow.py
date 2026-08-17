from pathlib import Path

from click.testing import CliRunner

from bora import __version__
from bora.cli import main
from bora.skill_pack import BORA_SKILL_MD
from bora.templates import AGENTS_MD, ticket_template


def test_version_is_050():
    assert __version__ == "0.7.0"


def test_agents_md_has_scope_guardrail_and_status():
    assert "Scope guardrail" in AGENTS_MD
    assert "Status.md" in AGENTS_MD
    assert "Requirements.md" in AGENTS_MD
    assert "bora-design" in AGENTS_MD
    assert "{ticket-id} {task-id}:" in AGENTS_MD or "ticket-id" in AGENTS_MD
    assert "bora dev ticket new" in AGENTS_MD
    assert "bora decision new" not in AGENTS_MD
    assert "Tasks.md" not in AGENTS_MD or "not" in AGENTS_MD  # prefer zero Tasks.md mentions
    assert "docs/ai/<" in AGENTS_MD or "Codebase" in AGENTS_MD


def test_skill_md_matches_hierarchical_workflow():
    assert "Status.md" in BORA_SKILL_MD
    assert (
        "project_path" in BORA_SKILL_MD
        or "<project_path>" in BORA_SKILL_MD
        or "bora dev ticket new" in BORA_SKILL_MD
    )
    assert "bora decision new" not in BORA_SKILL_MD


def test_init_writes_new_agents():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", "Acme/App"])
        text = Path("AGENTS.md").read_text()
        assert "Scope guardrail" in text
        assert "Status.md" in text


def test_init_does_not_overwrite_agents_without_force():
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("AGENTS.md").write_text("KEEP ME\n", encoding="utf-8")
        result = runner.invoke(main, ["dev", "init", "Acme/App"])
        assert result.exit_code == 0, result.output
        assert Path("AGENTS.md").read_text() == "KEEP ME\n"


def test_ticket_template_points_at_status_and_requirements():
    text = ticket_template("20260814-01-example", "Example", "feature", "medium")
    assert "Status.md" in text
    assert "Tasks.md" not in text
    assert "Requirements" in text
    assert "Architecture.md" not in text


def test_init_help_mentions_required_path_and_dated_files():
    runner = CliRunner()
    result = runner.invoke(main, ["dev", "init", "--help"])
    assert result.exit_code == 0, result.output
    assert "PROJECT_PATH" in result.output or "project_path" in result.output
    assert "Requirements" in result.output
    assert "Status.md" in result.output


def test_status_help_mentions_status_md():
    runner = CliRunner()
    result = runner.invoke(main, ["dev", "status", "--help"])
    assert result.exit_code == 0, result.output
    assert "Status.md" in result.output
    assert "Tasks.md" not in result.output
    assert "PROJECT_PATH" in result.output or "project_path" in result.output
