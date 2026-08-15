"""Bora 0.6.0: expanded skill pack, Cursor install, stricter lint."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from bora import __version__
from bora.cli import main
from bora.skill import PACK_SKILLS, SKILL_TEMPLATES, TOOLS, is_bora_skill
from bora.skill_pack import PACK_SKILL_NAMES_RE
from bora.templates import AGENTS_MD, AGENTS_TEMPLATE_VERSION
import re

SAMPLE = "Acme/Auth"

_OWNED_NAME_RE = re.compile(
    rf"^name:\s*({PACK_SKILL_NAMES_RE})\s*$",
    re.MULTILINE,
)


@pytest.fixture
def runner():
    return CliRunner()


def test_version_is_060():
    assert __version__ == "0.6.0"
    assert AGENTS_TEMPLATE_VERSION == "0.6.0"


def test_skill_pack_has_ten_trigger_only_descriptions():
    assert len(PACK_SKILLS) == 10
    assert set(PACK_SKILLS) == {
        "bora",
        "bora-plan",
        "bora-tdd",
        "bora-execute",
        "bora-design",
        "bora-worktree",
        "bora-review",
        "bora-debug",
        "bora-verify",
        "bora-finish",
    }
    for name, text in SKILL_TEMPLATES.items():
        assert text.startswith("---\nname: " + name)
        desc_line = [ln for ln in text.splitlines() if ln.startswith("description:")][0]
        assert "Use when" in desc_line
        assert len(desc_line) < 600


def test_owned_name_re_matches_all_pack_skills():
    for name in PACK_SKILLS:
        sample = f"---\nname: {name}\n---\n"
        assert _OWNED_NAME_RE.search(sample), name


def test_cursor_tool_registered():
    assert "cursor" in TOOLS
    assert TOOLS["cursor"].global_dir == Path.home() / ".cursor" / "skills"
    assert TOOLS["cursor"].project_dir == Path(".cursor") / "skills"


def test_skill_install_cursor_project(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        result = runner.invoke(main, ["dev", "skill", "install", "cursor", "--project"])
        assert result.exit_code == 0, result.output
        for name in PACK_SKILLS:
            md = Path(".cursor") / "skills" / name / "SKILL.md"
            assert md.exists(), name
            assert is_bora_skill(md)


def test_skill_install_all_includes_cursor(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        result = runner.invoke(main, ["dev", "skill", "install", "all", "--project"])
        assert result.exit_code == 0, result.output
        assert (Path(".cursor") / "skills" / "bora-finish" / "SKILL.md").exists()


def test_agents_md_055_content():
    assert 'version="0.6.0"' in AGENTS_MD
    assert "bora-design" in AGENTS_MD
    assert "bora-finish" in AGENTS_MD
    assert "origin_branch" in AGENTS_MD


def test_lint_errors_in_progress_without_plan(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        result = runner.invoke(main, ["dev", "ticket", "new", SAMPLE, "X", "--no-edit"])
        assert result.exit_code == 0
        tickets = list(Path("docs/ai/Acme/Auth/tickets").glob("*.md"))
        path = tickets[0]
        text = path.read_text()
        path.write_text(text.split("## Implementation plan")[0] + "## Notes\n", encoding="utf-8")
        runner.invoke(main, ["dev", "ticket", "set", SAMPLE, "01", "status", "in-progress"])
        result = runner.invoke(main, ["dev", "lint", SAMPLE])
        assert result.exit_code == 1
        assert "error" in (result.stderr + result.output).lower()
        assert "implementation plan" in (result.stderr + result.output).lower()


def test_lint_errors_in_progress_with_empty_plan(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        runner.invoke(main, ["dev", "ticket", "new", SAMPLE, "X", "--no-edit"])
        tickets = list(Path("docs/ai/Acme/Auth/tickets").glob("*.md"))
        path = tickets[0]
        text = path.read_text()
        empty_plan = """
## Implementation plan

Status: draft
Current task:

## Notes
"""
        path.write_text(text.split("## Implementation plan")[0] + empty_plan, encoding="utf-8")
        runner.invoke(main, ["dev", "ticket", "set", SAMPLE, "01", "status", "in-progress"])
        result = runner.invoke(main, ["dev", "lint", SAMPLE])
        assert result.exit_code == 1
        assert "Tnn" in (result.stderr + result.output) or "no ###" in (result.stderr + result.output).lower()


def test_upgrade_writes_060_agents(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        Path("AGENTS.md").write_text("# Old agents\n", encoding="utf-8")
        result = runner.invoke(main, ["dev", "upgrade"])
        assert result.exit_code == 0, result.output
        text = Path("AGENTS.md").read_text()
        assert 'version="0.6.0"' in text
        assert "bora-design" in text
        assert "bora-finish" in text
