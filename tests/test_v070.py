"""Bora 0.7.0: model-tier vocabulary and .bora/models.yaml resolution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bora import __version__
from bora.profile import CURRENT_VERSION
from bora.templates import AGENTS_TEMPLATE_VERSION
from bora.routing import (
    DEFAULT_SKILL_TIERS,
    VALID_TIERS,
    RoutingConfigError,
    load_models_config,
    resolve_effective_routing,
)

EXPECTED_DEFAULT_SKILL_TIERS = {
    "bora": "standard",
    "bora-design": "premium",
    "bora-plan": "premium",
    "bora-tdd": "premium",
    "bora-execute": "standard",
    "bora-worktree": "economy",
    "bora-verify": "economy",
    "bora-review": "premium",
    "bora-debug": "premium",
    "bora-finish": "economy",
}

VALID_YAML = """\
routing:
  enabled: true
  tiers:
    premium: auto/smart
    standard: auto/coding
    economy: auto/cheap
    local: auto/offline
  skills:
    bora-review: economy
"""


def _write_models_yaml(root: Path, text: str) -> Path:
    path = root / ".bora" / "models.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_valid_tiers_and_default_skill_map():
    assert frozenset(VALID_TIERS) == frozenset(
        {"premium", "standard", "economy", "local"}
    )
    assert len(VALID_TIERS) == 4
    assert DEFAULT_SKILL_TIERS == EXPECTED_DEFAULT_SKILL_TIERS


def test_missing_models_yaml_is_disabled_not_error(tmp_path):
    load_models_config(tmp_path)
    resolved = resolve_effective_routing(tmp_path)
    assert resolved.enabled is False
    assert resolved.skill_tiers == DEFAULT_SKILL_TIERS


def test_valid_models_yaml_enables_and_maps_tiers(tmp_path):
    _write_models_yaml(tmp_path, VALID_YAML)
    resolved = resolve_effective_routing(tmp_path)
    assert resolved.enabled is True
    assert resolved.tiers["premium"] == ["auto/smart"]
    assert resolved.skill_tiers["bora-review"] == "economy"
    for skill, tier in DEFAULT_SKILL_TIERS.items():
        if skill == "bora-review":
            continue
        assert resolved.skill_tiers[skill] == tier


def test_enabled_false_keeps_defaults(tmp_path):
    _write_models_yaml(
        tmp_path,
        """\
routing:
  enabled: false
  tiers:
    premium: auto/smart
    standard: auto/coding
    economy: auto/cheap
    local: auto/offline
""",
    )
    resolved = resolve_effective_routing(tmp_path)
    assert resolved.enabled is False


def test_invalid_tier_name_raises(tmp_path):
    _write_models_yaml(
        tmp_path,
        """\
routing:
  enabled: true
  tiers:
    ultra: auto/smart
""",
    )
    with pytest.raises(RoutingConfigError):
        load_models_config(tmp_path)


def test_unknown_skill_override_raises(tmp_path):
    _write_models_yaml(
        tmp_path,
        """\
routing:
  enabled: true
  tiers:
    premium: auto/smart
    standard: auto/coding
    economy: auto/cheap
    local: auto/offline
  skills:
    not-a-bora-skill: economy
""",
    )
    with pytest.raises(RoutingConfigError):
        load_models_config(tmp_path)


def test_skill_override_does_not_mutate_skill_source(tmp_path):
    skill_path = tmp_path / "SKILL.md"
    original = b"---\nname: bora-review\n---\nfixed-bytes\n"
    skill_path.write_bytes(original)
    _write_models_yaml(tmp_path, VALID_YAML)
    resolve_effective_routing(tmp_path)
    assert skill_path.read_bytes() == original


def test_invalid_yaml_raises_routing_config_error(tmp_path):
    _write_models_yaml(tmp_path, "routing:\n  enabled: [\n")
    with pytest.raises(RoutingConfigError, match="[Ii]nvalid"):
        load_models_config(tmp_path)


def test_invalid_skill_override_tier_raises(tmp_path):
    _write_models_yaml(
        tmp_path,
        """\
routing:
  enabled: true
  tiers:
    premium: auto/smart
    standard: auto/coding
    economy: auto/cheap
    local: auto/offline
  skills:
    bora-review: ultra
""",
    )
    with pytest.raises(RoutingConfigError):
        load_models_config(tmp_path)


# ---------------------------------------------------------------------------
# bora dev routing show (CLI)
# ---------------------------------------------------------------------------

from click.testing import CliRunner

from bora.cli import main

SAMPLE = "Acme/Auth"


def test_routing_show_disabled_without_models_yaml():
    runner = CliRunner()
    with runner.isolated_filesystem():
        init = runner.invoke(main, ["dev", "init", SAMPLE])
        assert init.exit_code == 0, init.output
        result = runner.invoke(main, ["dev", "routing", "show", SAMPLE])
        assert result.exit_code == 0, result.output
        assert "Status: disabled" in result.output
        for tier in ("premium", "standard", "economy", "local"):
            assert tier in result.output


def test_routing_show_enabled_prints_mappings():
    runner = CliRunner()
    with runner.isolated_filesystem():
        init = runner.invoke(main, ["dev", "init", SAMPLE])
        assert init.exit_code == 0, init.output
        _write_models_yaml(Path("."), VALID_YAML)
        result = runner.invoke(main, ["dev", "routing", "show", SAMPLE])
        assert result.exit_code == 0, result.output
        assert "Status: enabled" in result.output
        for identifier in ("auto/smart", "auto/coding", "auto/cheap", "auto/offline"):
            assert identifier in result.output


def test_routing_show_invalid_yaml_exits_nonzero():
    runner = CliRunner()
    with runner.isolated_filesystem():
        init = runner.invoke(main, ["dev", "init", SAMPLE])
        assert init.exit_code == 0, init.output
        _write_models_yaml(Path("."), "routing:\n  enabled: [\n")
        result = runner.invoke(main, ["dev", "routing", "show", SAMPLE])
        assert result.exit_code != 0
        combined = (result.output or "") + (result.stderr or "")
        assert "traceback" not in combined.lower()
        assert "configuration error" in combined.lower()


def test_routing_show_makes_no_network_calls(monkeypatch):
    import socket
    import urllib.request

    def _fail_urlopen(*_args, **_kwargs):
        pytest.fail("unexpected urllib.request.urlopen")

    def _fail_connect(*_args, **_kwargs):
        pytest.fail("unexpected socket.create_connection")

    monkeypatch.setattr(urllib.request, "urlopen", _fail_urlopen)
    monkeypatch.setattr(socket, "create_connection", _fail_connect)

    runner = CliRunner()
    with runner.isolated_filesystem():
        init = runner.invoke(main, ["dev", "init", SAMPLE])
        assert init.exit_code == 0, init.output
        without = runner.invoke(main, ["dev", "routing", "show", SAMPLE])
        assert without.exit_code == 0, without.output
        _write_models_yaml(Path("."), VALID_YAML)
        with_yaml = runner.invoke(main, ["dev", "routing", "show", SAMPLE])
        assert with_yaml.exit_code == 0, with_yaml.output


# ---------------------------------------------------------------------------
# Version, upgrade, and 0.6.x compatibility
# ---------------------------------------------------------------------------


def test_version_is_070():
    assert __version__ == "0.8.0"
    assert AGENTS_TEMPLATE_VERSION == "0.8.0"
    assert CURRENT_VERSION == "0.8.0"


def test_init_does_not_create_models_yaml():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["dev", "init", SAMPLE])
        assert result.exit_code == 0, result.output
        assert Path(".bora/profile.json").exists()
        assert not Path(".bora/models.yaml").exists()


def test_upgrade_does_not_create_models_yaml():
    runner = CliRunner()
    with runner.isolated_filesystem():
        init = runner.invoke(main, ["dev", "init", SAMPLE])
        assert init.exit_code == 0, init.output
        install = runner.invoke(main, ["dev", "skill", "install", "cursor", "--project"])
        assert install.exit_code == 0, install.output
        upgrade = runner.invoke(main, ["dev", "upgrade"])
        assert upgrade.exit_code == 0, upgrade.output
        assert not Path(".bora/models.yaml").exists()


def test_upgrade_rewrites_skills_without_touching_project_docs():
    runner = CliRunner()
    with runner.isolated_filesystem():
        init = runner.invoke(main, ["dev", "init", SAMPLE])
        assert init.exit_code == 0, init.output
        project = Path("docs/ai/Acme/Auth")
        before = {
            path: path.read_bytes()
            for path in project.rglob("*")
            if path.is_file()
        }
        install = runner.invoke(main, ["dev", "skill", "install", "cursor", "--project"])
        assert install.exit_code == 0, install.output
        upgrade = runner.invoke(main, ["dev", "upgrade"])
        assert upgrade.exit_code == 0, upgrade.output
        after = {
            path: path.read_bytes()
            for path in project.rglob("*")
            if path.is_file()
        }
        assert after == before
        skill = Path(".cursor/skills/bora/SKILL.md")
        assert skill.exists()
        assert "model_tier" in skill.read_text(encoding="utf-8")


def test_06x_profile_still_loads():
    runner = CliRunner()
    with runner.isolated_filesystem():
        init = runner.invoke(main, ["dev", "init", SAMPLE])
        assert init.exit_code == 0, init.output
        path = Path(".bora/profile.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["version"] = "0.6.0"
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        status = runner.invoke(main, ["dev", "status", SAMPLE])
        assert status.exit_code == 0, status.output
        lint = runner.invoke(main, ["dev", "lint", SAMPLE])
        assert lint.exit_code == 0, lint.output
        show = runner.invoke(main, ["dev", "routing", "show", SAMPLE])
        assert show.exit_code == 0, show.output
        assert not Path(".bora/models.yaml").exists()


def test_readme_routing_is_advanced_not_quickstart():
    readme = Path("README.md").read_text(encoding="utf-8")
    quote = (
        "Bora does not choose models. Bora identifies the relative "
        "reasoning requirements of its workflows and optionally communicates "
        "those requirements to compatible routing systems."
    )
    assert quote in readme
    start = readme.find("## Quick start (dev)")
    end = readme.find("## Workflow cycle")
    assert start != -1 and end != -1 and start < end
    quickstart = readme[start:end]
    assert "models.yaml" not in quickstart
