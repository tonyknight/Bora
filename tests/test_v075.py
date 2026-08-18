"""Bora 0.7.5: ordered catalog lists, opt-in, session resolve."""

from __future__ import annotations

from pathlib import Path

import pytest

from bora.routing import (
    DEFAULT_SKILL_TIERS,
    RoutingConfigError,
    load_models_config,
    resolve_effective_routing,
)


def _write_models_yaml(root: Path, text: str) -> Path:
    path = root / ".bora" / "models.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


LIST_YAML = """\
routing:
  enabled: true
  tiers:
    premium:
      - grok latest high
      - claude opus
      - gpt-5
    standard:
      - composer
      - sonnet
      - gpt-5-mini
    economy:
      - glm latest
      - haiku
      - gpt-5-nano
    local:
      - ollama
  skills:
    bora-review: economy
"""

CSV_YAML = """\
routing:
  enabled: true
  tiers:
    premium: "grok latest high, claude opus, gpt-5"
    standard: composer, sonnet, gpt-5-mini
    economy: " glm latest , haiku , gpt-5-nano "
    local: ollama
"""

SCALAR_YAML = """\
routing:
  enabled: true
  tiers:
    premium: auto/smart
    standard: auto/coding
    economy: auto/cheap
    local: auto/offline
"""

FIVE_YAML = """\
routing:
  enabled: true
  tiers:
    premium:
      - a
      - b
      - c
      - d
      - e
    standard: one
    economy: two
    local: three
"""


def test_yaml_list_parses_in_order(tmp_path):
    _write_models_yaml(tmp_path, LIST_YAML)
    resolved = resolve_effective_routing(tmp_path)
    assert resolved.enabled is True
    assert resolved.tiers["premium"] == [
        "grok latest high",
        "claude opus",
        "gpt-5",
    ]
    assert resolved.tiers["standard"] == ["composer", "sonnet", "gpt-5-mini"]
    assert resolved.tiers["economy"] == ["glm latest", "haiku", "gpt-5-nano"]
    assert resolved.tiers["local"] == ["ollama"]
    assert resolved.skill_tiers["bora-review"] == "economy"


def test_csv_string_splits_and_strips(tmp_path):
    _write_models_yaml(tmp_path, CSV_YAML)
    resolved = resolve_effective_routing(tmp_path)
    assert resolved.tiers["premium"] == [
        "grok latest high",
        "claude opus",
        "gpt-5",
    ]
    assert resolved.tiers["standard"] == ["composer", "sonnet", "gpt-5-mini"]
    assert resolved.tiers["economy"] == ["glm latest", "haiku", "gpt-5-nano"]
    assert resolved.tiers["local"] == ["ollama"]


def test_scalar_string_becomes_one_item_list(tmp_path):
    _write_models_yaml(tmp_path, SCALAR_YAML)
    resolved = resolve_effective_routing(tmp_path)
    assert resolved.tiers["premium"] == ["auto/smart"]
    assert resolved.tiers["standard"] == ["auto/coding"]
    assert resolved.tiers["economy"] == ["auto/cheap"]
    assert resolved.tiers["local"] == ["auto/offline"]


def test_empty_yaml_sequence_raises(tmp_path):
    _write_models_yaml(
        tmp_path,
        """\
routing:
  enabled: true
  tiers:
    premium: []
""",
    )
    with pytest.raises(RoutingConfigError):
        load_models_config(tmp_path)


def test_empty_string_raises(tmp_path):
    _write_models_yaml(
        tmp_path,
        """\
routing:
  enabled: true
  tiers:
    premium: "   "
""",
    )
    with pytest.raises(RoutingConfigError):
        load_models_config(tmp_path)


def test_csv_empty_tokens_only_raises(tmp_path):
    _write_models_yaml(
        tmp_path,
        """\
routing:
  enabled: true
  tiers:
    premium: ", , ,"
""",
    )
    with pytest.raises(RoutingConfigError):
        load_models_config(tmp_path)


def test_five_aliases_allowed(tmp_path):
    _write_models_yaml(tmp_path, FIVE_YAML)
    resolved = resolve_effective_routing(tmp_path)
    assert resolved.tiers["premium"] == ["a", "b", "c", "d", "e"]


def test_missing_models_yaml_is_disabled_not_error(tmp_path):
    load_models_config(tmp_path)
    resolved = resolve_effective_routing(tmp_path)
    assert resolved.enabled is False
    assert resolved.tiers == {}
    assert resolved.skill_tiers == DEFAULT_SKILL_TIERS


def test_unknown_skill_override_raises(tmp_path):
    _write_models_yaml(
        tmp_path,
        """\
routing:
  enabled: true
  tiers:
    premium: auto/smart
  skills:
    not-a-bora-skill: economy
""",
    )
    with pytest.raises(RoutingConfigError):
        load_models_config(tmp_path)
