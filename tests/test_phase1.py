"""Phase 1 integration smoke tests: profile system and CLI routing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from bora.cli import main
from bora.profile import read_profile, write_profile


@pytest.fixture
def runner():
    return CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# dev init
# ---------------------------------------------------------------------------


def test_dev_init_creates_profile(runner):
    with runner.isolated_filesystem() as td:
        result = runner.invoke(main, ["dev", "init"])
        assert result.exit_code == 0, result.output
        prof = json.loads(Path(".bora/profile.json").read_text())
        assert prof["profile"] == "dev"
        assert prof["version"] == "0.3.0"
        assert "initialized_at" in prof


def test_dev_init_creates_scaffold_files(runner):
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["dev", "init"])
        assert result.exit_code == 0, result.output
        assert Path("AGENTS.md").exists()
        assert Path("docs/ai/Project.md").exists()
        assert Path("docs/ai/Architecture.md").exists()
        assert Path("docs/ai/Tasks.md").exists()
        assert Path("docs/ai/tickets").is_dir()


def test_dev_init_refuses_to_overwrite_without_force(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init"])
        result = runner.invoke(main, ["dev", "init"])
        assert result.exit_code == 1
        assert "Refusing to overwrite" in result.stderr


def test_dev_init_force_overwrites(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init"])
        result = runner.invoke(main, ["dev", "init", "--force"])
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Profile locking
# ---------------------------------------------------------------------------


def test_dev_command_blocked_in_write_project(runner):
    with runner.isolated_filesystem() as td:
        root = Path(td)
        # Create a write profile project
        write_profile(root, "write")
        (root / "AGENTS.md").write_text("", encoding="utf-8")
        (root / "docs" / "ai" / "tickets").mkdir(parents=True)

        result = runner.invoke(main, ["dev", "status"])
        assert result.exit_code == 1
        assert "Profile locked" in result.stderr


def test_write_command_blocked_in_dev_project(runner):
    with runner.isolated_filesystem() as td:
        root = Path(td)
        runner.invoke(main, ["dev", "init"])

        # Add a placeholder write subcommand isn't possible yet (Phase 2),
        # but we can verify by patching profile to write and running dev command.
        data = json.loads((root / ".bora" / "profile.json").read_text())
        data["profile"] = "write"
        (root / ".bora" / "profile.json").write_text(json.dumps(data))

        result = runner.invoke(main, ["dev", "status"])
        assert result.exit_code == 1
        assert "Profile locked" in result.stderr


def test_skip_profile_check_bypasses_locking(runner):
    with runner.isolated_filesystem() as td:
        root = Path(td)
        runner.invoke(main, ["dev", "init"])

        # Flip to write profile
        data = json.loads((root / ".bora" / "profile.json").read_text())
        data["profile"] = "write"
        (root / ".bora" / "profile.json").write_text(json.dumps(data))

        result = runner.invoke(main, ["--skip-profile-check", "dev", "status"])
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Help filtering
# ---------------------------------------------------------------------------


def test_help_hides_write_in_dev_project(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init"])
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Write Profile Commands" not in result.output
        assert "Dev Profile Commands" in result.output


def test_help_hides_dev_in_write_project(runner):
    with runner.isolated_filesystem() as td:
        root = Path(td)
        write_profile(root, "write")
        (root / "AGENTS.md").write_text("", encoding="utf-8")
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Dev Profile Commands" not in result.output
        assert "Write Profile Commands" in result.output


def test_help_shows_both_without_profile(runner):
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Dev Profile Commands" in result.output
        assert "Write Profile Commands" in result.output


# ---------------------------------------------------------------------------
# Upgrade prompt (no profile.json)
# ---------------------------------------------------------------------------


def test_upgrade_prompt_creates_profile_on_dev_choice(runner):
    with runner.isolated_filesystem() as td:
        root = Path(td)
        # Create scaffold without profile (simulate pre-0.3.0 project)
        (root / "AGENTS.md").write_text("", encoding="utf-8")
        (root / "docs" / "ai" / "tickets").mkdir(parents=True)

        # Answer 'dev' to the prompt
        result = runner.invoke(main, ["dev", "status"], input="dev\n")
        assert result.exit_code == 0, result.output
        prof = json.loads((root / ".bora" / "profile.json").read_text())
        assert prof["profile"] == "dev"


def test_upgrade_prompt_blocks_when_wrong_profile_chosen(runner):
    with runner.isolated_filesystem() as td:
        root = Path(td)
        (root / "AGENTS.md").write_text("", encoding="utf-8")
        (root / "docs" / "ai" / "tickets").mkdir(parents=True)

        # Answer 'write' when running a dev command — should block
        result = runner.invoke(main, ["dev", "status"], input="write\n")
        assert result.exit_code == 1
        assert "Profile locked" in result.stderr
