"""Bora 0.7.0: skill pack model_tier metadata and advisory routing notes."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from bora.cli import main
from bora.routing import DEFAULT_SKILL_TIERS
from bora.skill_pack import PACK_SKILLS, SKILL_TEMPLATES

SAMPLE = "Acme/Auth"

FORBIDDEN_PROVIDER_FRAGMENTS = (
    "claude-sonnet",
    "gemini-flash",
    "gpt-4",
    "openai/",
    "anthropic/",
)


@pytest.fixture
def runner():
    return CliRunner()


def _frontmatter(text: str) -> dict:
    assert text.startswith("---\n"), text[:40]
    end = text.find("\n---\n", 4)
    assert end != -1
    data = yaml.safe_load(text[4:end])
    assert isinstance(data, dict)
    return data


def test_default_skill_tiers_cover_pack():
    assert set(DEFAULT_SKILL_TIERS) == set(PACK_SKILLS)


def test_installed_skills_contain_model_tier(runner):
    with runner.isolated_filesystem():
        init = runner.invoke(main, ["dev", "init", SAMPLE])
        assert init.exit_code == 0, init.output
        result = runner.invoke(main, ["dev", "skill", "install", "cursor", "--project"])
        assert result.exit_code == 0, result.output
        for name in PACK_SKILLS:
            md = Path(".cursor") / "skills" / name / "SKILL.md"
            text = md.read_text(encoding="utf-8")
            assert text.startswith("---\nname: " + name)
            fm = _frontmatter(text)
            keys = list(fm)
            assert keys[:3] == ["name", "description", "model_tier"], keys
            assert fm["model_tier"] == DEFAULT_SKILL_TIERS[name]


def test_skill_templates_have_no_provider_model_names():
    from bora.skill_pack import render_pack_skill

    blob = "\n".join(render_pack_skill(name) for name in PACK_SKILLS).lower()
    for fragment in FORBIDDEN_PROVIDER_FRAGMENTS:
        assert fragment not in blob, fragment


def test_verify_debug_execute_activity_hints():
    from bora.skill_pack import render_pack_skill

    verify = render_pack_skill("bora-verify").lower()
    debug = render_pack_skill("bora-debug").lower()
    execute = render_pack_skill("bora-execute").lower()
    assert "economy" in verify
    assert "premium" in debug
    assert "bora-verify" in execute and "economy" in execute
    assert "bora-debug" in execute and "premium" in execute


def test_skill_bodies_include_advisory_routing_note():
    from bora.skill_pack import render_pack_skill

    for name in PACK_SKILLS:
        text = render_pack_skill(name).lower()
        assert "model_tier" in text
        assert "does not choose models" in text or "advisory" in text


def test_source_templates_still_start_with_name_frontmatter():
    """Keep the v0.5.5 pack-shape constraint on SKILL_TEMPLATES."""
    for name, text in SKILL_TEMPLATES.items():
        assert text.startswith("---\nname: " + name)
