"""Bora 0.7.0: model-tier vocabulary and .bora/models.yaml resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

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
    assert resolved.tiers["premium"] == "auto/smart"
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
