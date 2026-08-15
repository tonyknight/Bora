"""Bora 0.5.0: implementation plans on tickets, skill pack, upgrade."""

from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path

import pytest
from click.testing import CliRunner

from bora import __version__
from bora.cli import main
from bora.lint import lint_ticket
from bora.plan import (
    VALID_PLAN_STATUSES,
    extract_plan_section,
    parse_plan_tasks,
    set_plan_status_line,
    set_task_checkbox,
)
from bora.skill import PACK_SKILLS, SKILL_TEMPLATES
from bora.templates import (
    AGENTS_MD,
    AGENTS_TEMPLATE_VERSION,
    REQUIREMENTS_MD_TEMPLATE,
    ticket_template,
)
from bora.ticket import parse_ticket

SAMPLE = "Acme/Auth"


@pytest.fixture
def runner():
    return CliRunner()


def _init_and_ticket(runner, title="Add login"):
    runner.invoke(main, ["dev", "init", SAMPLE])
    result = runner.invoke(main, ["dev", "ticket", "new", SAMPLE, title, "--no-edit"])
    assert result.exit_code == 0, result.output
    tickets = list(Path("docs/ai/Acme/Auth/tickets").glob("*.md"))
    assert len(tickets) == 1
    return tickets[0]


# ---------------------------------------------------------------------------
# Version / templates
# ---------------------------------------------------------------------------


def test_version_is_050():
    assert __version__ == "0.5.0"
    assert AGENTS_TEMPLATE_VERSION == "0.5.0"


def test_ticket_template_has_implementation_plan_section():
    text = ticket_template("20260814-01-example", "Example", "feature", "medium")
    assert "## Implementation plan" in text
    assert "Status: draft" in text
    assert "Current task:" in text
    assert "plan_status:" not in text.split("---", 2)[1]


def test_agents_md_has_managed_markers_and_commit_contract():
    assert "bora-managed:start version=\"0.5.0\"" in AGENTS_MD
    assert "bora-managed:end" in AGENTS_MD
    assert "## Project-specific instructions" in AGENTS_MD
    assert "{ticket-id} {task-id}:" in AGENTS_MD
    assert "bora-execute" in AGENTS_MD
    assert "bora-plan" in AGENTS_MD
    assert "bora-tdd" in AGENTS_MD
    assert "should I continue" not in AGENTS_MD.lower() or "never ask" in AGENTS_MD.lower()


def test_requirements_template_commit_contract():
    text = REQUIREMENTS_MD_TEMPLATE.format(today="2026-08-14", project_name="Auth")
    assert "{ticket-id} {task-id}:" in text
    assert "xcodebuild" in text
    assert "implementation plan is written on the ticket" in text.lower() or "on the ticket" in text.lower()


def test_init_writes_managed_agents(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        text = Path("AGENTS.md").read_text()
        assert "bora-managed:start version=\"0.5.0\"" in text
        assert "## Project-specific instructions" in text


# ---------------------------------------------------------------------------
# Plan parser
# ---------------------------------------------------------------------------


PLAN_BODY = """## Description

A ticket.

## Implementation plan

Status: draft
Current task:

### T01: add target
- **Files:** app.xcodeproj
- **Verify:** xcodebuild -list
- **Commit:** `id T01: add target`
- [ ] done

### T02: entitlements
- **Files:** App.entitlements
- **Verify:** xcodebuild test
- **Commit:** `id T02: entitlements`
- [ ] done

## Notes
"""


def test_extract_and_parse_plan_tasks():
    section = extract_plan_section(PLAN_BODY)
    assert section is not None
    assert "### T01:" in section
    tasks = parse_plan_tasks(section)
    assert [t.id for t in tasks] == ["T01", "T02"]
    assert tasks[0].title == "add target"
    assert tasks[0].done is False


def test_set_task_checkbox_advances_current():
    body = set_task_checkbox(PLAN_BODY, "T01", done=True)
    section = extract_plan_section(body)
    tasks = parse_plan_tasks(section)
    assert tasks[0].done is True
    assert tasks[1].done is False
    assert "Current task: T02" in section


def test_set_plan_status_line():
    body = set_plan_status_line(PLAN_BODY, "in-progress")
    assert "Status: in-progress" in extract_plan_section(body)


def test_extract_missing_section():
    assert extract_plan_section("## Description\n\nNope.\n") is None


# ---------------------------------------------------------------------------
# CLI plan commands
# ---------------------------------------------------------------------------


def test_plan_show_prints_section(runner):
    with runner.isolated_filesystem():
        _init_and_ticket(runner)
        result = runner.invoke(main, ["dev", "plan", "show", SAMPLE, "01"])
        assert result.exit_code == 0, result.output
        assert "## Implementation plan" in result.output
        assert "Status: draft" in result.output


def test_plan_show_errors_without_section(runner):
    with runner.isolated_filesystem():
        path = _init_and_ticket(runner)
        text = path.read_text()
        path.write_text(text.replace("## Implementation plan", "## Other"), encoding="utf-8")
        result = runner.invoke(main, ["dev", "plan", "show", SAMPLE, "01"])
        assert result.exit_code == 1
        assert "Implementation plan" in result.stderr


def test_plan_set_status_in_progress_sets_ticket(runner):
    with runner.isolated_filesystem():
        path = _init_and_ticket(runner)
        result = runner.invoke(main, ["dev", "plan", "set", SAMPLE, "01", "status", "in-progress"])
        assert result.exit_code == 0, result.output
        t = parse_ticket(path)
        assert t.frontmatter.get("plan_status") == "in-progress"
        assert t.status == "in-progress"
        assert "Status: in-progress" in t.body


def test_plan_set_done_does_not_close_ticket(runner):
    with runner.isolated_filesystem():
        path = _init_and_ticket(runner)
        runner.invoke(main, ["dev", "plan", "set", SAMPLE, "01", "status", "in-progress"])
        result = runner.invoke(main, ["dev", "plan", "set", SAMPLE, "01", "status", "done"])
        assert result.exit_code == 0, result.output
        t = parse_ticket(path)
        assert t.frontmatter.get("plan_status") == "done"
        assert t.status == "in-progress"
        assert not t.frontmatter.get("closed")


def test_plan_set_blocked_blocks_ticket(runner):
    with runner.isolated_filesystem():
        path = _init_and_ticket(runner)
        result = runner.invoke(main, ["dev", "plan", "set", SAMPLE, "01", "status", "blocked"])
        assert result.exit_code == 0, result.output
        t = parse_ticket(path)
        assert t.status == "blocked"
        assert t.frontmatter.get("plan_status") == "blocked"


def test_plan_task_done_checks_box_and_status(runner):
    with runner.isolated_filesystem():
        path = _init_and_ticket(runner)
        body = path.read_text()
        plan = """
## Implementation plan

Status: draft
Current task:

### T01: one
- [ ] done

### T02: two
- [ ] done
"""
        path.write_text(body.replace("## Implementation plan\n\nStatus: draft\nCurrent task:\n", plan), encoding="utf-8")
        result = runner.invoke(main, ["dev", "plan", "task", SAMPLE, "01", "T01", "done"])
        assert result.exit_code == 0, result.output
        t = parse_ticket(path)
        tasks = parse_plan_tasks(extract_plan_section(t.body))
        assert tasks[0].done is True
        assert t.frontmatter.get("current_task") == "T02"
        assert t.frontmatter.get("plan_status") == "in-progress"

        result = runner.invoke(main, ["dev", "plan", "task", SAMPLE, "01", "T02", "done"])
        assert result.exit_code == 0, result.output
        t = parse_ticket(path)
        assert t.frontmatter.get("plan_status") == "done"
        assert not t.frontmatter.get("current_task")


def test_plan_set_invalid_status(runner):
    with runner.isolated_filesystem():
        _init_and_ticket(runner)
        result = runner.invoke(main, ["dev", "plan", "set", SAMPLE, "01", "status", "planned"])
        assert result.exit_code == 1
        for allowed in VALID_PLAN_STATUSES:
            assert allowed in result.stderr


def test_no_plan_new_command(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        result = runner.invoke(main, ["dev", "plan", "new", SAMPLE, "01"])
        assert result.exit_code != 0


def test_status_shows_plan_progress(runner):
    with runner.isolated_filesystem():
        path = _init_and_ticket(runner, "Add target")
        runner.invoke(main, ["dev", "ticket", "set", SAMPLE, "01", "status", "in-progress"])
        body = path.read_text()
        plan = """
## Implementation plan

Status: in-progress
Current task: T02

### T01: one
- [x] done

### T02: two
- [ ] done

### T03: three
- [ ] done
"""
        path.write_text(body.split("## Implementation plan")[0] + plan, encoding="utf-8")
        t = parse_ticket(path)
        t.set_field("plan_status", "in-progress")
        t.set_field("current_task", "T02")
        t.save()
        result = runner.invoke(main, ["dev", "status", SAMPLE])
        assert result.exit_code == 0, result.output
        status = Path("docs/ai/Acme/Auth/Status.md").read_text()
        assert "plan in-progress" in status
        assert "T02/T03" in status or "1/3" in status


def test_lint_warns_in_progress_without_plan(runner):
    with runner.isolated_filesystem():
        path = _init_and_ticket(runner)
        text = path.read_text()
        # Remove the implementation plan section entirely
        path.write_text(text.split("## Implementation plan")[0] + "## Notes\n", encoding="utf-8")
        runner.invoke(main, ["dev", "ticket", "set", SAMPLE, "01", "status", "in-progress"])
        result = runner.invoke(main, ["dev", "lint", SAMPLE])
        assert result.exit_code == 0  # warning, not error
        assert "warning" in result.stderr.lower() or "warning" in result.output.lower()
        assert "implementation plan" in (result.stderr + result.output).lower()


def test_lint_old_ticket_without_plan_is_clean():
    from bora.ticket import Ticket

    t = Ticket(
        path=Path("20260814-01-old.md"),
        frontmatter={
            "id": "20260814-01-old",
            "title": "Old",
            "type": "feature",
            "priority": "medium",
            "status": "todo",
            "created": date.today(),
        },
        body="## Description\n\nLegacy ticket.\n",
    )
    issues = lint_ticket(t, {"20260814-01-old"})
    assert issues == []


def test_lint_duplicate_task_ids():
    from bora.ticket import Ticket

    ticket = Ticket(
        path=Path("20260814-01-dup.md"),
        frontmatter={
            "id": "20260814-01-dup",
            "title": "Dup",
            "type": "feature",
            "priority": "medium",
            "status": "todo",
            "created": date.today(),
            "plan_status": "draft",
            "current_task": "T99",
        },
        body="""## Implementation plan

### T01: one
- [ ] done

### T01: again
- [ ] done
""",
    )
    issues = lint_ticket(ticket, {"20260814-01-dup"})
    messages = " ".join(i.message for i in issues)
    assert "duplicate" in messages.lower()
    assert "T99" in messages or "current_task" in messages


# ---------------------------------------------------------------------------
# Skill pack
# ---------------------------------------------------------------------------


def test_skill_pack_has_four_trigger_only_descriptions():
    assert set(PACK_SKILLS) == {"bora", "bora-plan", "bora-tdd", "bora-execute"}
    for name, text in SKILL_TEMPLATES.items():
        assert text.startswith("---\nname: " + name)
        desc_line = [ln for ln in text.splitlines() if ln.startswith("description:")][0]
        assert "Use when" in desc_line
        assert len(desc_line) < 600


def test_skill_install_writes_pack(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        result = runner.invoke(main, ["dev", "skill", "install", "claude", "--project"])
        assert result.exit_code == 0, result.output
        for name in PACK_SKILLS:
            md = Path(".claude") / "skills" / name / "SKILL.md"
            assert md.exists(), name
            assert f"name: {name}" in md.read_text()


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def test_upgrade_rewrites_unmarked_agents(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        Path("AGENTS.md").write_text("# Old agents\nKeep nothing.\n", encoding="utf-8")
        result = runner.invoke(main, ["dev", "upgrade"])
        assert result.exit_code == 0, result.output
        text = Path("AGENTS.md").read_text()
        assert "bora-managed:start version=\"0.5.0\"" in text
        assert "bora-execute" in text
        assert "## Project-specific instructions" in text
        prof = json.loads(Path(".bora/profile.json").read_text())
        assert prof["version"] == "0.5.0"


def test_upgrade_preserves_user_section(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        text = Path("AGENTS.md").read_text()
        text = text.replace(
            "Add local rules below this heading. `bora dev upgrade` never overwrites\nthis section.\n",
            "Never delete the Share Extension App Group.\n",
        )
        Path("AGENTS.md").write_text(text, encoding="utf-8")
        # Pretend the managed block is old
        text = Path("AGENTS.md").read_text().replace('version="0.5.0"', 'version="0.4.5"')
        Path("AGENTS.md").write_text(text, encoding="utf-8")
        result = runner.invoke(main, ["dev", "upgrade"])
        assert result.exit_code == 0, result.output
        out = Path("AGENTS.md").read_text()
        assert 'version="0.5.0"' in out
        assert "Never delete the Share Extension App Group." in out


def test_upgrade_dry_run_does_not_write(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        Path("AGENTS.md").write_text("# Old\n", encoding="utf-8")
        result = runner.invoke(main, ["dev", "upgrade", "--dry-run"])
        assert result.exit_code == 0, result.output
        assert Path("AGENTS.md").read_text() == "# Old\n"


def test_upgrade_refuses_dirty_unmarked_agents(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.t"], check=True)
        subprocess.run(["git", "config", "user.name", "t"], check=True)
        Path("AGENTS.md").write_text("# committed\n", encoding="utf-8")
        subprocess.run(["git", "add", "AGENTS.md"], check=True)
        subprocess.run(["git", "commit", "-m", "a"], check=True, capture_output=True)
        Path("AGENTS.md").write_text("# dirty unmarked\n", encoding="utf-8")
        result = runner.invoke(main, ["dev", "upgrade"])
        assert result.exit_code == 1
        assert "stash" in result.stderr.lower() or "commit" in result.stderr.lower()
        assert Path("AGENTS.md").read_text() == "# dirty unmarked\n"


def test_stale_agents_hint_on_status(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        Path("AGENTS.md").write_text("# Old agents\n", encoding="utf-8")
        result = runner.invoke(main, ["dev", "status", SAMPLE])
        assert result.exit_code == 0, result.output
        assert "bora dev upgrade" in result.stderr
        assert "not in sync" in result.stderr.lower()


def test_upgrade_without_dev_profile_errors(runner):
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["dev", "upgrade"])
        assert result.exit_code != 0


def test_upgrade_agents_only_does_not_rewrite_skills(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        runner.invoke(main, ["dev", "skill", "install", "claude", "--project"])
        skill = Path(".claude/skills/bora/SKILL.md")
        skill.write_text("# mutated skill\n", encoding="utf-8")
        Path("AGENTS.md").write_text("# Old agents\n", encoding="utf-8")
        result = runner.invoke(main, ["dev", "upgrade", "--agents-only"])
        assert result.exit_code == 0, result.output
        assert "bora-managed:start version=\"0.5.0\"" in Path("AGENTS.md").read_text()
        assert skill.read_text() == "# mutated skill\n"


def test_upgrade_skills_only_does_not_rewrite_agents(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        runner.invoke(main, ["dev", "skill", "install", "claude", "--project"])
        Path("AGENTS.md").write_text("# Old agents\n", encoding="utf-8")
        result = runner.invoke(main, ["dev", "upgrade", "--skills-only"])
        assert result.exit_code == 0, result.output
        assert Path("AGENTS.md").read_text() == "# Old agents\n"
        text = Path(".claude/skills/bora-execute/SKILL.md").read_text()
        assert "name: bora-execute" in text


def test_upgrade_preserves_initialized_at(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        prof_path = Path(".bora/profile.json")
        data = json.loads(prof_path.read_text())
        data["version"] = "0.4.5"
        data["initialized_at"] = "2026-01-01T00:00:00+00:00"
        prof_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        result = runner.invoke(main, ["dev", "upgrade"])
        assert result.exit_code == 0, result.output
        out = json.loads(prof_path.read_text())
        assert out["version"] == "0.5.0"
        assert out["initialized_at"] == "2026-01-01T00:00:00+00:00"
