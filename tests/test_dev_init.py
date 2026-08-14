from datetime import date
from pathlib import Path

import pytest
from click.testing import CliRunner
from bora.cli import main

SAMPLE = "QromaCore/Hamburg/Gallery Refactor"


@pytest.fixture
def runner():
    return CliRunner()


def test_init_requires_path(runner):
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["dev", "init"])
        assert result.exit_code != 0


def test_init_rejects_depth_1(runner):
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["dev", "init", "Foo"])
        assert result.exit_code == 1
        assert "two segments" in result.stderr.lower() or "at least two" in result.stderr.lower()


def test_init_scaffolds_dated_files(runner):
    with runner.isolated_filesystem() as td:
        result = runner.invoke(main, ["dev", "init", SAMPLE])
        assert result.exit_code == 0, result.output
        today = date.today().isoformat()
        base = Path("docs/ai/QromaCore/Hamburg/Gallery Refactor")
        assert (base / f"({today}) Gallery Refactor.md").exists()
        assert (base / f"({today}) Gallery Refactor Requirements.md").exists()
        assert (base / "Status.md").exists()
        assert (base / "tickets").is_dir()
        assert Path("AGENTS.md").exists()
        assert Path(".bora/profile.json").exists()
        assert not Path(".bora/project.json").exists()
        assert not Path("docs/ai/Project.md").exists()
        assert not Path("docs/ai/Architecture.md").exists()
        assert not Path("docs/ai/Tasks.md").exists()


def test_init_tags_frontmatter(runner):
    with runner.isolated_filesystem():
        result = runner.invoke(
            main,
            ["dev", "init", SAMPLE, "--tags", 'Codebase,"Release Train",Project'],
        )
        assert result.exit_code == 0, result.output
        today = date.today().isoformat()
        text = Path(
            f"docs/ai/QromaCore/Hamburg/Gallery Refactor/({today}) Gallery Refactor.md"
        ).read_text()
        assert "codebase: QromaCore" in text
        assert "release_train: Hamburg" in text


def test_init_tag_count_mismatch(runner):
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["dev", "init", SAMPLE, "--tags", "Codebase,Project"])
        assert result.exit_code == 1
        assert "tags" in result.stderr.lower()


def test_init_collision_without_force(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        result = runner.invoke(main, ["dev", "init", SAMPLE])
        assert result.exit_code == 1
        assert "Refusing to overwrite" in result.stderr


def test_init_force_does_not_duplicate_dated_files(runner):
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE])
        result = runner.invoke(main, ["dev", "init", SAMPLE, "--force"])
        assert result.exit_code == 0, result.output
        base = Path("docs/ai/QromaCore/Hamburg/Gallery Refactor")
        briefings = list(base.glob("*) Gallery Refactor.md"))
        briefings = [p for p in base.iterdir() if p.name.endswith("Gallery Refactor.md") and "Requirements" not in p.name]
        assert len(briefings) == 1
